# code-review-graph CLI Reference

This document provides a detailed reference for all commands available in the `code-review-graph` CLI. Each command corresponds to an underlying MCP tool, and the descriptions below are pulled directly from the official tool definitions.

## Core Management

Basic commands for setting up and maintaining your code knowledge graph.

### `code-review-graph install` (alias: `init`)
*   **Purpose:** Register the MCP server with AI coding platforms (Claude Code, Cursor, etc.).
*   **Args:**
    *   `--repo`: Repository root (auto-detected).
    *   `--platform`: Target platform (e.g., `claude`, `cursor`, `gemini-cli`). Default: `all`.
    *   `--dry-run`: Show what would be done without writing files.
    *   `--no-instructions`: Skip injecting graph instructions into `CLAUDE.md`, etc.

### `code-review-graph build`
*   **Purpose:** Full graph build (re-parse all files).
*   **Args:**
    *   `--repo`: Repository root (auto-detected).
    *   `--skip-postprocess`: Skip all post-processing (raw parse only).
    *   `--data-dir`: External directory to store graph database.

### `code-review-graph update`
*   **Purpose:** Incremental update (only changed files).
*   **Args:**
    *   `--base`: Git ref for incremental diff (default: `HEAD~1`).
    *   `--repo`: Repository root (auto-detected).

### `code-review-graph status`
*   **Purpose:** Show graph statistics (nodes, edges, languages, last updated).

---

## Advanced Analysis (Tool Reference)

These commands expose the full power of the internal MCP tools. All output is formatted as structured JSON by default.

### `code-review-graph detect-changes`
*   **Description:** Detect changes and produce risk-scored review guidance. Primary tool for code review. Maps git diffs to affected functions, flows, communities, and test coverage gaps. Returns priority-ordered review guidance with risk scores.
*   **Usage:** `code-review-graph detect-changes [--base BASE] [--brief]`
*   **Args:**
    *   `--base`: Git ref to diff against (default: `HEAD~1`).
    *   `--brief`: Show brief summary only (for human output).
    *   `--include-source`: Include source code snippets for changed functions.
    *   `--max-depth`: Impact radius depth for BFS traversal (default: 2).
    *   `--detail-level`: "standard" (full) or "minimal" (summary).
*   **Output:** Risk-scored analysis with changed functions, affected flows, test gaps, and review priorities.

### `code-review-graph get-impact-radius`
*   **Description:** Analyze the blast radius of changed files.
*   **Usage:** `code-review-graph get-impact-radius [FILES...] [--max-depth N]`
*   **Args:**
    *   `changed_files`: Explicit list of changed file paths. If omitted, auto-detects from git.
    *   `--max-depth`: How many hops to traverse in the graph (default: 2).
    *   `--max-results`: Maximum impacted nodes to return (default: 500).
    *   `--detail-level`: "standard" (full) or "minimal" (summary).
*   **Output:** JSON containing `changed_nodes`, `impacted_nodes`, `impacted_files`, and connecting `edges`.

### `code-review-graph semantic-search`
*   **Description:** Search for nodes by name, keyword, or semantic similarity. Uses hybrid search (FTS5 BM25 + vector embeddings) as the primary search path.
*   **Usage:** `code-review-graph semantic-search "query" [--kind KIND]`
*   **Args:**
    *   `query`: Search string to match against node names and qualified names.
    *   `--kind`: Optional filter by node kind (File, Class, Function, Type, Test).
    *   `--limit`: Maximum results to return (default: 20).
*   **Output:** Ranked list of matching nodes with similarity scores.

### `code-review-graph query-graph`
*   **Description:** Run a predefined graph query.
*   **Usage:** `code-review-graph query-graph PATTERN TARGET`
*   **Args:**
    *   `pattern`: Query pattern. One of: `callers_of`, `callees_of`, `imports_of`, `importers_of`, `children_of`, `tests_for`, `inheritors_of`, `file_summary`.
    *   `target`: The node name, qualified name, or file path to query about.
*   **Output:** Matching nodes and edges for the specific structural relationship.

### `code-review-graph list-flows`
*   **Description:** List execution flows in the codebase, sorted by criticality. Each flow represents a call chain starting from an entry point (e.g., HTTP handler, CLI command, test function).
*   **Usage:** `code-review-graph list-flows [--sort-by COL] [--limit N]`
*   **Args:**
    *   `--sort-by`: Sort column: `criticality`, `depth`, `node_count`, `file_count`, or `name`.
    *   `--kind`: Optional filter by entry point kind (e.g., "Test", "Function").
*   **Output:** List of flows with criticality scores and metadata.

### `code-review-graph get-flow`
*   **Description:** Get details of a single execution flow. Retrieves full path details, including each step's function name, file, and line numbers.
*   **Usage:** `code-review-graph get-flow --id ID [--include-source]`
*   **Args:**
    *   `--id`: Database ID of the flow (from `list-flows`).
    *   `--name`: Name to search for (partial match).
    *   `--include-source`: Include source code snippets for each step.
*   **Output:** Step-by-step path details for the specific flow.

### `code-review-graph list-communities`
*   **Description:** List detected code communities in the codebase. Each community represents a cluster of related code entities (functions, classes).
*   **Usage:** `code-review-graph list-communities [--sort-by COL]`
*   **Args:**
    *   `--sort-by`: Sort column: `size`, `cohesion`, or `name`.
    *   `--min-size`: Minimum community size to include.
*   **Output:** List of communities with size and cohesion scores.

### `code-review-graph get-architecture-overview`
*   **Description:** Generate an architecture overview based on community structure. Builds a high-level view by analyzing community boundaries and cross-community coupling.
*   **Output:** JSON map of communities, cross-community edges, and coupling warnings.

### `code-review-graph refactor`
*   **Description:** Unified refactoring entry point. Supports `rename` (preview), `dead_code` (find unused), and `suggest` (community-driven suggestions).
*   **Usage:** `code-review-graph refactor --mode rename --old-name A --new-name B`
*   **Args:**
    *   `--mode`: One of `rename`, `dead_code`, or `suggest`.
    *   `--old-name`: (rename mode) Current symbol name.
    *   `--new-name`: (rename mode) Desired new name.
*   **Output:** Preview of changes and a `refactor_id` needed for application.

### `code-review-graph apply-refactor`
*   **Description:** Apply a previously previewed refactoring to source files. Performs exact string replacements.
*   **Usage:** `code-review-graph apply-refactor ID [--dry-run]`
*   **Args:**
    *   `refactor_id`: ID returned by a prior `refactor` call.
    *   `--dry-run`: Return a unified diff without touching disk.
*   **Output:** Count of applied edits and modified files.

### `code-review-graph get-hub-nodes`
*   **Description:** Find the most connected nodes (hotspots) in the codebase graph. Changes to them have disproportionate blast radius.
*   **Args:** `--top-n`: Number of top hubs to return (default: 10).

### `code-review-graph get-bridge-nodes`
*   **Description:** Find architectural chokepoints via betweenness centrality. These nodes sit on shortest paths between many node pairs.
*   **Args:** `--top-n`: Number of top bridges to return (default: 10).

### `code-review-graph get-knowledge-gaps`
*   **Description:** Identify structural weaknesses, including isolated nodes, thin communities, and untested hotspots.

### `code-review-graph find-large-functions`
*   **Description:** Find functions, classes, or files exceeding a line-count threshold. Useful for code-quality audits.
*   **Args:**
    *   `--min-lines`: Minimum line count to flag (default: 50).
    *   `--kind`: Filter by Function, Class, File, or Test.

### `code-review-graph embed-graph`
*   **Description:** Compute vector embeddings for all graph nodes to enable semantic search.
*   **Args:**
    *   `--model`: Embedding model name.
    *   `--provider`: `local`, `openai`, `google`, or `minimax`.

### `code-review-graph generate-wiki`
*   **Description:** Generate a markdown wiki from the community structure. Creates a page for each community in `.code-review-graph/wiki/`.

### `code-review-graph get-suggested-questions`
*   **Description:** Auto-generate review questions from graph analysis about chokepoints, untested hubs, and coupling.

### `code-review-graph traverse-graph`
*   **Description:** BFS/DFS traversal from a starting node.
*   **Args:**
    *   `query`: Search string to find the starting node.
    *   `--mode`: `bfs` or `dfs`.
    *   `--depth`: Max traversal depth (1-6).

---

## Multi-Repo Commands

Manage multiple repositories in a single registry.

### `code-review-graph register <path> [--alias name]`
*   **Purpose:** Register a repository in the global registry.

### `code-review-graph repos`
*   **Purpose:** List registered repositories (human-readable).

### `code-review-graph list-repos`
*   **Purpose:** List registered repositories in structured JSON format.

### `code-review-graph cross-repo-search "query"`
*   **Purpose:** Search across all registered repositories' graph databases.

---

## Daemon (Background Watcher)

Manage the background daemon that keeps your graphs up-to-date automatically.

*   `code-review-graph daemon start [--foreground]`
*   `code-review-graph daemon stop`
*   `code-review-graph daemon status`
*   `code-review-graph daemon logs [--repo ALIAS]`
*   `code-review-graph daemon add <path>`
*   `code-review-graph daemon remove <path_or_alias>`
