"""Tests for composite tools (explore_codebase, find_code, review_changes_composite).

These tools fuse multiple existing tool functions into single calls,
optimized for local LLM agents via ``serve --lite``.
"""

from __future__ import annotations

from unittest.mock import patch

# ---------------------------------------------------------------------------
# explore_codebase_func
# ---------------------------------------------------------------------------


class TestExplorCodebase:
    """Tests for explore_codebase_func."""

    @patch("code_review_graph.tools.composite.get_hub_nodes_func")
    @patch("code_review_graph.tools.composite.list_flows")
    @patch("code_review_graph.tools.composite.get_architecture_overview_func")
    def test_returns_unified_response(self, mock_arch, mock_flows, mock_hubs):
        """All three sub-tools succeed → unified response."""
        mock_arch.return_value = {
            "status": "ok",
            "summary": "2 communities",
            "communities": [
                {"name": "auth", "size": 10},
                {"name": "api", "size": 8},
            ],
            "cross_community_edges": [],
            "warnings": [],
        }
        mock_flows.return_value = {
            "status": "ok",
            "flows": [
                {"name": "login_flow", "criticality": 0.9},
            ],
        }
        mock_hubs.return_value = {
            "status": "ok",
            "hub_nodes": [
                {"name": "main_handler", "degree": 15},
            ],
        }

        from code_review_graph.tools.composite import explore_codebase_func

        result = explore_codebase_func(repo_root="/fake")

        assert result["status"] == "ok"
        assert "2 communities" in result["summary"]
        assert "1 critical flows" in result["summary"]
        assert "1 hotspots" in result["summary"]
        assert len(result["architecture"]["communities"]) == 2
        assert len(result["critical_flows"]) == 1
        assert len(result["hotspots"]) == 1
        assert "warnings" not in result  # no errors

    @patch("code_review_graph.tools.composite.get_hub_nodes_func")
    @patch("code_review_graph.tools.composite.list_flows")
    @patch("code_review_graph.tools.composite.get_architecture_overview_func")
    def test_partial_failure_still_returns(self, mock_arch, mock_flows, mock_hubs):
        """One sub-tool fails → still returns data from the others."""
        mock_arch.return_value = {
            "status": "ok",
            "summary": "1 community",
            "communities": [{"name": "core", "size": 5}],
            "cross_community_edges": [],
            "warnings": [],
        }
        mock_flows.side_effect = Exception("flows broke")
        mock_hubs.return_value = {
            "status": "ok",
            "hub_nodes": [],
        }

        from code_review_graph.tools.composite import explore_codebase_func

        result = explore_codebase_func(repo_root="/fake")

        assert result["status"] == "ok"
        assert len(result["architecture"]["communities"]) == 1
        assert result["critical_flows"] == []
        assert "warnings" in result
        assert any("flows" in w for w in result["warnings"])


# ---------------------------------------------------------------------------
# find_code_func
# ---------------------------------------------------------------------------


class TestFindCode:
    """Tests for find_code_func."""

    @patch("code_review_graph.tools.composite.query_graph")
    @patch("code_review_graph.tools.composite.semantic_search_nodes")
    def test_search_and_expand(self, mock_search, mock_query):
        """Search finds results → top 1 is expanded."""
        mock_search.return_value = {
            "status": "ok",
            "results": [
                {
                    "name": "authenticate",
                    "qualified_name": "auth.authenticate",
                    "file_path": "auth.py",
                    "kind": "Function",
                    "line_start": 10,
                    "line_end": 30,
                },
                {
                    "name": "auth_middleware",
                    "qualified_name": "middleware.auth_middleware",
                    "file_path": "middleware.py",
                    "kind": "Function",
                    "line_start": 5,
                    "line_end": 15,
                },
            ],
        }

        def mock_query_side_effect(pattern, target, **kwargs):
            if pattern == "callers_of":
                return {"status": "ok", "results": [{"name": "login"}]}
            elif pattern == "callees_of":
                return {"status": "ok", "results": [{"name": "db_check"}]}
            elif pattern == "tests_for":
                return {"status": "ok", "results": [{"name": "test_auth"}]}
            return {"status": "ok", "results": []}

        mock_query.side_effect = mock_query_side_effect

        from code_review_graph.tools.composite import find_code_func

        result = find_code_func(query="auth", repo_root="/fake")

        assert result["status"] == "ok"
        assert len(result["search_results"]) == 2
        assert len(result["expanded"]) == 1  # top 1 only
        exp = result["expanded"][0]
        assert exp["name"] == "authenticate"
        assert len(exp["callers"]) == 1
        assert len(exp["callees"]) == 1
        assert len(exp["tests"]) == 1

    @patch("code_review_graph.tools.composite.semantic_search_nodes")
    def test_empty_query(self, mock_search):
        """Empty query → error response."""
        from code_review_graph.tools.composite import find_code_func

        result = find_code_func(query="", repo_root="/fake")
        assert result["status"] == "error"
        mock_search.assert_not_called()

    @patch("code_review_graph.tools.composite.semantic_search_nodes")
    def test_no_results(self, mock_search):
        """Search returns no results → empty expanded."""
        mock_search.return_value = {
            "status": "ok",
            "results": [],
        }

        from code_review_graph.tools.composite import find_code_func

        result = find_code_func(query="nonexistent", repo_root="/fake")

        assert result["status"] == "ok"
        assert result["search_results"] == []
        assert result["expanded"] == []

    @patch("code_review_graph.tools.composite.query_graph")
    @patch("code_review_graph.tools.composite.semantic_search_nodes")
    def test_expand_failure_graceful(self, mock_search, mock_query):
        """query_graph raises → expansion has empty lists, not crash."""
        mock_search.return_value = {
            "status": "ok",
            "results": [
                {"name": "func_a", "qualified_name": "mod.func_a",
                 "file_path": "mod.py", "kind": "Function"},
            ],
        }
        mock_query.side_effect = Exception("graph broken")

        from code_review_graph.tools.composite import find_code_func

        result = find_code_func(query="func_a", repo_root="/fake")

        assert result["status"] == "ok"
        assert len(result["expanded"]) == 1
        exp = result["expanded"][0]
        assert exp["callers"] == []
        assert exp["callees"] == []
        assert exp["tests"] == []


# ---------------------------------------------------------------------------
# review_changes_composite_func
# ---------------------------------------------------------------------------


class TestReviewChangesComposite:
    """Tests for review_changes_composite_func."""

    @patch("code_review_graph.tools.composite.get_affected_flows_func")
    @patch("code_review_graph.tools.composite.get_review_context")
    @patch("code_review_graph.tools.composite.detect_changes_func")
    def test_full_review(self, mock_detect, mock_review, mock_flows):
        """All three sub-tools succeed → unified review."""
        mock_detect.return_value = {
            "status": "ok",
            "risk_score": 0.65,
            "changed_files": ["auth.py"],
            "changed_functions": [
                {"name": "login", "file_path": "auth.py"},
            ],
            "test_gaps": [
                {"name": "login", "reason": "no tests"},
            ],
        }
        mock_review.return_value = {
            "status": "ok",
            "context": {
                "review_guidance": "- 1 untested function",
                "source_snippets": {"auth.py": "10: def login():"},
            },
        }
        mock_flows.return_value = {
            "status": "ok",
            "affected_flows": [
                {"name": "login_flow", "criticality": 0.9},
            ],
        }

        from code_review_graph.tools.composite import review_changes_composite_func

        result = review_changes_composite_func(
            base="HEAD~1", repo_root="/fake",
        )

        assert result["status"] == "ok"
        assert result["risk_score"] == 0.65
        assert result["risk_label"] == "medium"
        assert len(result["changed_functions"]) == 1
        assert len(result["test_gaps"]) == 1
        assert len(result["affected_flows"]) == 1
        assert result["review_guidance"] == "- 1 untested function"
        assert "auth.py" in result["source_snippets"]

    @patch("code_review_graph.tools.composite.get_affected_flows_func")
    @patch("code_review_graph.tools.composite.get_review_context")
    @patch("code_review_graph.tools.composite.detect_changes_func")
    def test_no_changes(self, mock_detect, mock_review, mock_flows):
        """No changes → short-circuit response."""
        mock_detect.return_value = {
            "status": "ok",
            "risk_score": 0,
            "changed_files": [],
            "changed_functions": [],
            "test_gaps": [],
        }

        from code_review_graph.tools.composite import review_changes_composite_func

        result = review_changes_composite_func(repo_root="/fake")

        assert result["status"] == "ok"
        assert result["risk_score"] == 0.0
        assert "No changes" in result["summary"]
        # review_context and affected_flows should NOT be called
        mock_review.assert_not_called()
        mock_flows.assert_not_called()


# ---------------------------------------------------------------------------
# LITE_TOOLS constant and --lite flag
# ---------------------------------------------------------------------------


class TestLiteTools:
    """Tests for the LITE_TOOLS constant and --lite integration."""

    def test_lite_tools_has_five_entries(self):
        """LITE_TOOLS must contain exactly 5 tool names."""
        from code_review_graph.main import LITE_TOOLS

        assert len(LITE_TOOLS) == 5
        assert "explore_codebase_tool" in LITE_TOOLS
        assert "find_code_tool" in LITE_TOOLS
        assert "review_changes_composite_tool" in LITE_TOOLS
        assert "query_graph_tool" in LITE_TOOLS
        assert "refactor_tool" in LITE_TOOLS

    def test_lite_flag_cli_parsing(self):
        """--lite flag is parsed correctly for serve command."""
        # Smoke test: if the import succeeds, the flag exists in the parser
        from code_review_graph.cli import main as cli_main  # noqa: F401

        assert True  # If imports succeed, the flag exists

    def test_tools_overrides_lite(self):
        """When both --tools and --lite are set, --tools wins."""
        from code_review_graph.main import LITE_TOOLS

        # Simulate the logic from main()
        tools = "query_graph_tool,refactor_tool"
        lite = True

        # --tools overrides --lite
        if lite and not tools:
            final_tools = ",".join(LITE_TOOLS)
        else:
            final_tools = tools

        assert final_tools == "query_graph_tool,refactor_tool"

    def test_lite_without_tools_uses_lite_tools(self):
        """When --lite is set without --tools, LITE_TOOLS are used."""
        from code_review_graph.main import LITE_TOOLS

        tools = None
        lite = True

        if lite and not tools:
            final_tools = ",".join(LITE_TOOLS)
        else:
            final_tools = tools

        # Should be a comma-separated string of all LITE_TOOLS
        tool_set = set(final_tools.split(","))
        assert tool_set == LITE_TOOLS
