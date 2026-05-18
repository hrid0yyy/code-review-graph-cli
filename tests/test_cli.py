"""Tests for CLI helpers and MCP serve command wiring."""

import logging
import sys
from importlib.metadata import PackageNotFoundError
from unittest.mock import MagicMock, patch

from code_review_graph import cli


def test_get_version_logs_and_falls_back_to_dev(monkeypatch, caplog):
    def _raise_package_not_found(_dist_name: str) -> str:
        raise PackageNotFoundError("code-review-graph")

    monkeypatch.setattr(cli, "pkg_version", _raise_package_not_found)

    with caplog.at_level(logging.DEBUG, logger="code_review_graph.cli"):
        version = cli._get_version()

    assert version == "dev"
    assert "Package metadata unavailable" in caplog.text


class TestServeCommand:
    def test_serve_passes_auto_watch_flag(self):
        argv = [
            "code-review-graph",
            "serve",
            "--repo",
            "repo-root",
            "--auto-watch",
        ]
        with patch.object(sys, "argv", argv):
            with patch("code_review_graph.main.main") as mock_serve:
                cli.main()

        mock_serve.assert_called_once_with(
            repo_root="repo-root",
            auto_watch=True,
            tools=None,
            lite=False,
        )

    def test_mcp_alias_maps_to_serve(self):
        argv = [
            "code-review-graph",
            "mcp",
            "--repo",
            "repo-root",
        ]
        with patch.object(sys, "argv", argv):
            with patch("code_review_graph.main.main") as mock_serve:
                cli.main()

        mock_serve.assert_called_once_with(
            repo_root="repo-root",
            auto_watch=False,
            lite=False,
        )


class TestWatchInteraction:
    def test_watch_exits_when_lock_is_held(self):
        argv = ["code-review-graph", "watch", "--repo", "repo-root"]
        with patch.object(sys, "argv", argv):
            with patch("code_review_graph.graph.GraphStore") as mock_store:
                mock_store.return_value = MagicMock()
                with patch("code_review_graph.incremental.get_db_path") as mock_db:
                    mock_db.return_value = MagicMock()
                    with patch("code_review_graph.incremental.watch") as mock_watch:
                        mock_watch.side_effect = RuntimeError("watcher already running")
                        try:
                            cli.main()
                            assert False, "Expected SystemExit"
                        except SystemExit as exc:
                            assert exc.code == 1


import pytest

@pytest.mark.parametrize("command, args, expected_tool_func", [
    ("get-impact-radius", ["file1.py"], "get_impact_radius"),
    ("query-graph", ["callers_of", "myfunc"], "query_graph"),
    ("semantic-search", ["search query"], "semantic_search_nodes"),
    ("get-review-context", ["file1.py"], "get_review_context"),
    ("get-affected-flows", ["file1.py"], "get_affected_flows_func"),
    ("list-flows", ["--limit", "10"], "list_flows"),
    ("get-flow", ["--id", "1"], "get_flow"),
    ("list-communities", ["--min-size", "5"], "list_communities_func"),
    ("get-community", ["--id", "2"], "get_community_func"),
    ("get-architecture-overview", [], "get_architecture_overview_func"),
    ("embed-graph", ["--provider", "openai"], "embed_graph"),
    ("get-docs-section", ["usage"], "get_docs_section"),
    ("find-large-functions", ["--min-lines", "100"], "find_large_functions"),
    ("get-hub-nodes", ["--top-n", "5"], "get_hub_nodes_func"),
    ("get-bridge-nodes", ["--top-n", "5"], "get_bridge_nodes_func"),
    ("get-knowledge-gaps", [], "get_knowledge_gaps_func"),
    ("get-surprising-connections", ["--top-n", "5"], "get_surprising_connections_func"),
    ("get-suggested-questions", [], "get_suggested_questions_func"),
    ("traverse-graph", ["start_node"], "traverse_graph_func"),
    ("refactor", ["--mode", "rename", "--old-name", "A", "--new-name", "B"], "refactor_func"),
    ("apply-refactor", ["ref123"], "apply_refactor_func"),
    ("get-wiki-page", ["MyComm"], "get_wiki_page_func"),
    ("cross-repo-search", ["query"], "cross_repo_search_func"),
    ("list-graph-stats", [], "list_graph_stats"),
    ("list-repos", [], "list_repos_func"),
    ("build-or-update-graph", ["--rebuild"], "build_or_update_graph"),
    ("generate-wiki", ["--force"], "generate_wiki_func"),
])
def test_tool_command_dispatch(command, args, expected_tool_func):
    """Verify that each tool subcommand calls the correct tool function."""
    with patch(f"code_review_graph.tools.{expected_tool_func}") as mock_tool:
        mock_tool.return_value = {"status": "ok"}

        # Mock sys.argv for the command
        with patch("sys.argv", ["code-review-graph", command] + args):
            with patch("builtins.print") as mock_print:
                cli.main()

                # Check if mock_tool was called
                assert mock_tool.called

                # Check if JSON was printed
                assert mock_print.called
                print_args = mock_print.call_args[0][0]
                assert '"status": "ok"' in print_args


def test_detect_changes_dispatch():
    """Verify detect-changes calls the tool and handles --brief."""
    with patch("code_review_graph.tools.review.detect_changes_func") as mock_tool:
        mock_tool.return_value = {"status": "ok", "summary": "brief summary"}

        # JSON mode (default)
        with patch("sys.argv", ["code-review-graph", "detect-changes"]):
            with patch("builtins.print") as mock_print:
                cli.main()
                assert mock_tool.called
                assert '"status": "ok"' in mock_print.call_args[0][0]

        mock_tool.reset_mock()

        # Brief mode
        with patch("sys.argv", ["code-review-graph", "detect-changes", "--brief"]):
            with patch("builtins.print") as mock_print:
                cli.main()
                assert mock_tool.called
                assert mock_print.call_args[0][0] == "brief summary"
