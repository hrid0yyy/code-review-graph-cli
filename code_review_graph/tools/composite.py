"""Composite tools optimized for local LLM agents.

Three high-level tools that fuse multiple existing tool functions into
single calls, reducing the number of tool invocations an agent needs.

Used with ``code-review-graph serve --lite`` to expose only 5 tools
(these 3 + query_graph + refactor_tool).
"""

from __future__ import annotations

import logging
from typing import Any

from ._common import _error_response
from .analysis_tools import get_hub_nodes_func
from .community_tools import get_architecture_overview_func
from .flows_tools import list_flows
from .query import query_graph, semantic_search_nodes
from .review import detect_changes_func, get_affected_flows_func, get_review_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Composite 1: explore_codebase
# ---------------------------------------------------------------------------


def explore_codebase_func(
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Full codebase exploration in a single call.

    Combines architecture overview, critical execution flows, and
    architectural hotspots into one response.  Designed as the first
    tool an agent should call when entering an unfamiliar codebase.

    Internally calls:
    - get_architecture_overview_func → community map + coupling warnings
    - list_flows (limit=10) → top 10 critical execution paths
    - get_hub_nodes_func (top_n=5) → top 5 architectural hotspots

    Args:
        repo_root: Repository root path. Auto-detected if omitted.

    Returns:
        Unified dict with architecture, critical_flows, and hotspots.
    """
    errors: list[str] = []

    # 1. Architecture overview
    architecture: dict[str, Any] = {}
    try:
        arch_result = get_architecture_overview_func(repo_root=repo_root)
        if arch_result.get("status") == "ok":
            architecture = {
                k: v for k, v in arch_result.items()
                if k not in ("status", "_hints")
            }
        else:
            errors.append(f"architecture: {arch_result.get('error', 'unknown')}")
    except Exception as exc:
        logger.debug("explore_codebase: architecture failed: %s", exc)
        errors.append(f"architecture: {exc}")

    # 2. Critical flows (top 10)
    critical_flows: list[Any] = []
    try:
        flows_result = list_flows(
            repo_root=repo_root, sort_by="criticality",
            limit=10, detail_level="minimal",
        )
        if flows_result.get("status") == "ok":
            critical_flows = flows_result.get("flows", [])
        else:
            errors.append(f"flows: {flows_result.get('error', 'unknown')}")
    except Exception as exc:
        logger.debug("explore_codebase: flows failed: %s", exc)
        errors.append(f"flows: {exc}")

    # 3. Hub nodes (top 5)
    hotspots: list[Any] = []
    try:
        hubs_result = get_hub_nodes_func(repo_root=repo_root, top_n=5)
        if hubs_result.get("status") == "ok":
            hotspots = hubs_result.get("hub_nodes", [])
        else:
            errors.append(f"hotspots: {hubs_result.get('error', 'unknown')}")
    except Exception as exc:
        logger.debug("explore_codebase: hub nodes failed: %s", exc)
        errors.append(f"hotspots: {exc}")

    # Build summary
    n_communities = len(architecture.get("communities", []))
    n_flows = len(critical_flows)
    n_hotspots = len(hotspots)
    summary = (
        f"Codebase overview: {n_communities} communities, "
        f"{n_flows} critical flows, {n_hotspots} hotspots."
    )

    result: dict[str, Any] = {
        "status": "ok",
        "summary": summary,
        "architecture": architecture,
        "critical_flows": critical_flows,
        "hotspots": hotspots,
    }
    if errors:
        result["warnings"] = errors
    return result


# ---------------------------------------------------------------------------
# Composite 2: find_code
# ---------------------------------------------------------------------------


def find_code_func(
    query: str,
    kind: str | None = None,
    expand_top_n: int = 1,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Search for code and auto-expand relationships of top results.

    Combines semantic search with automatic relationship expansion.
    Searches for code entities by name or concept, then for the top N
    results automatically retrieves callers, callees, and test coverage.

    Args:
        query: Search string to match against node names or concepts.
        kind: Optional filter: Function, Class, File, Type, or Test.
        expand_top_n: Number of top results to auto-expand with
            relationship data.  Default: 1.
        repo_root: Repository root path. Auto-detected if omitted.

    Returns:
        Search results plus expanded relationship data for top results.
    """
    if not query or not query.strip():
        return _error_response("query is required")

    # 1. Semantic search
    try:
        search_result = semantic_search_nodes(
            query=query, kind=kind, limit=20,
            repo_root=repo_root, detail_level="standard",
        )
    except Exception as exc:
        return _error_response(f"search failed: {exc}")

    if search_result.get("status") != "ok":
        return search_result

    results = search_result.get("results", [])
    if not results:
        return {
            "status": "ok",
            "summary": f"No results found for '{query}'.",
            "search_results": [],
            "expanded": [],
        }

    # 2. Expand top N results with callers/callees/tests
    expanded: list[dict[str, Any]] = []
    top_n = min(expand_top_n, len(results))

    for result_node in results[:top_n]:
        node_name = result_node.get("name", "")
        qualified = result_node.get("qualified_name", node_name)
        target = qualified or node_name

        if not target:
            continue

        expansion: dict[str, Any] = {
            "name": node_name,
            "qualified_name": qualified,
            "file": result_node.get("file_path", ""),
            "kind": result_node.get("kind", ""),
            "line_start": result_node.get("line_start"),
            "line_end": result_node.get("line_end"),
        }

        # Callers
        try:
            callers_result = query_graph(
                pattern="callers_of", target=target,
                repo_root=repo_root, detail_level="minimal",
            )
            if callers_result.get("status") == "ok":
                expansion["callers"] = callers_result.get("results", [])
            else:
                expansion["callers"] = []
        except Exception:
            expansion["callers"] = []

        # Callees
        try:
            callees_result = query_graph(
                pattern="callees_of", target=target,
                repo_root=repo_root, detail_level="minimal",
            )
            if callees_result.get("status") == "ok":
                expansion["callees"] = callees_result.get("results", [])
            else:
                expansion["callees"] = []
        except Exception:
            expansion["callees"] = []

        # Tests
        try:
            tests_result = query_graph(
                pattern="tests_for", target=target,
                repo_root=repo_root, detail_level="minimal",
            )
            if tests_result.get("status") == "ok":
                expansion["tests"] = tests_result.get("results", [])
            else:
                expansion["tests"] = []
        except Exception:
            expansion["tests"] = []

        expanded.append(expansion)

    # Build summary
    total = len(results)
    first_name = results[0].get("name", "unknown") if results else "none"
    summary = (
        f"Found {total} result(s) for '{query}'. "
        f"Top match: {first_name}"
    )
    if expanded:
        exp = expanded[0]
        n_callers = len(exp.get("callers", []))
        n_callees = len(exp.get("callees", []))
        n_tests = len(exp.get("tests", []))
        summary += (
            f" ({n_callers} callers, {n_callees} callees, "
            f"{n_tests} tests)"
        )

    return {
        "status": "ok",
        "summary": summary,
        "search_results": results,
        "expanded": expanded,
    }


# ---------------------------------------------------------------------------
# Composite 3: review_changes_composite
# ---------------------------------------------------------------------------


def review_changes_composite_func(
    base: str = "HEAD~1",
    include_source: bool = False,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """Complete code review in a single call.

    Combines change detection (risk scoring), review context (source
    snippets + guidance), and affected flow analysis into one unified
    response.  Designed as the safety-net tool an agent calls after
    making code changes.

    Internally calls:
    - detect_changes_func → risk scores + changed functions + test gaps
    - get_review_context → source snippets + review guidance
    - get_affected_flows_func → affected execution flows

    Args:
        base: Git ref to diff against.  Default: HEAD~1.
        include_source: Include source code snippets for changed
            functions.  Default: False.
        repo_root: Repository root path. Auto-detected if omitted.

    Returns:
        Unified review with risk_score, changed_functions,
        review_guidance, source_snippets, affected_flows, and test_gaps.
    """
    errors: list[str] = []

    # 1. Detect changes (primary — risk scoring)
    detect_result: dict[str, Any] = {}
    try:
        detect_result = detect_changes_func(
            base=base, include_source=include_source,
            repo_root=repo_root,
        )
    except Exception as exc:
        logger.debug("review_changes: detect_changes failed: %s", exc)
        errors.append(f"detect_changes: {exc}")

    # If no changes detected, short-circuit
    if (
        detect_result.get("status") == "ok"
        and detect_result.get("risk_score", 0) == 0
        and not detect_result.get("changed_functions")
    ):
        return {
            "status": "ok",
            "summary": "No changes detected. Nothing to review.",
            "risk_score": 0.0,
            "changed_functions": [],
            "review_guidance": "",
            "source_snippets": {},
            "affected_flows": [],
            "test_gaps": [],
        }

    # 2. Review context (source snippets + guidance)
    review_guidance = ""
    source_snippets: dict[str, Any] = {}
    try:
        review_result = get_review_context(
            base=base, include_source=True,
            repo_root=repo_root,
        )
        if review_result.get("status") == "ok":
            ctx = review_result.get("context", {})
            review_guidance = ctx.get("review_guidance", "")
            source_snippets = ctx.get("source_snippets", {})
        else:
            errors.append(
                f"review_context: {review_result.get('error', 'unknown')}"
            )
    except Exception as exc:
        logger.debug("review_changes: review_context failed: %s", exc)
        errors.append(f"review_context: {exc}")

    # 3. Affected flows
    affected_flows: list[Any] = []
    try:
        flows_result = get_affected_flows_func(
            base=base, repo_root=repo_root,
        )
        if flows_result.get("status") == "ok":
            affected_flows = flows_result.get("affected_flows", [])
        else:
            errors.append(
                f"affected_flows: {flows_result.get('error', 'unknown')}"
            )
    except Exception as exc:
        logger.debug("review_changes: affected_flows failed: %s", exc)
        errors.append(f"affected_flows: {exc}")

    # Build unified response
    risk_score = detect_result.get("risk_score", 0.0)
    changed_functions = detect_result.get("changed_functions", [])
    test_gaps = detect_result.get("test_gaps", [])
    changed_files = detect_result.get("changed_files", [])

    risk_label = (
        "high" if risk_score > 0.7
        else "medium" if risk_score > 0.4
        else "low"
    )

    summary_parts = [
        f"Review of {len(changed_files)} changed file(s): "
        f"risk {risk_label} ({risk_score:.2f}).",
    ]
    if changed_functions:
        summary_parts.append(
            f"{len(changed_functions)} function(s) changed."
        )
    if test_gaps:
        summary_parts.append(f"{len(test_gaps)} test gap(s).")
    if affected_flows:
        summary_parts.append(
            f"{len(affected_flows)} execution flow(s) affected."
        )

    result: dict[str, Any] = {
        "status": "ok",
        "summary": " ".join(summary_parts),
        "risk_score": risk_score,
        "risk_label": risk_label,
        "changed_files": changed_files,
        "changed_functions": changed_functions,
        "review_guidance": review_guidance,
        "source_snippets": source_snippets,
        "affected_flows": affected_flows,
        "test_gaps": test_gaps,
    }
    if errors:
        result["warnings"] = errors
    return result
