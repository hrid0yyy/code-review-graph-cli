# Strategic Tool Analysis: AI Agent Knowledge Acquisition

This guide analyzes the 28 available tools through the lens of **AI Agent Cognition**. For a coding agent (like Claude, Gemini, or a custom agent), "understanding" a codebase is not about reading every file; it is about building a structural and behavioral map.

---

## 1. Tool Clustering (Logical Domains)

### Cluster A: Architectural Mapping (The "Skeleton")
*Tools: `get_architecture_overview`, `list_communities`, `get_community`, `get_hub_nodes`, `get_bridge_nodes`.*
*   **Importance:** These tools define the boundaries of the system. In large projects, code is often logically grouped but physically scattered. These tools reveal the "true" modularity.

### Cluster B: Behavioral Analysis (The "Nervous System")
*Tools: `list_flows`, `get_flow`, `get_affected_flows`.*
*   **Importance:** Understanding *what* a component is (Cluster A) is different from understanding *what it does*. Flows represent the execution paths (e.g., "User Login -> Auth Check -> DB Query").

### Cluster C: Discovery & Navigation (The "Eyes")
*Tools: `semantic_search_nodes`, `query_graph`, `traverse_graph`, `cross_repo_search`.*
*   **Importance:** How the agent finds specific logic. Semantic search is for concepts ("how do we handle tokens?"); Query Graph is for relationships ("who calls this?").

### Cluster D: Change & Risk Intelligence (The "Safety Net")
*Tools: `detect_changes`, `get_impact_radius`, `get_review_context`, `get_suggested_questions`.*
*   **Importance:** Essential for coding. These tools prevent regressions by calculating the "Blast Radius" of a proposed change.

### Cluster E: Code Health & Maintenance (The "Audit")
*Tools: `get_knowledge_gaps`, `find_large_functions`, `get_surprising_connections`, `refactor`, `apply_refactor`.*
*   **Importance:** Used for refactoring tasks and identifying technical debt or architectural rot.

---

## 2. Top 5 "First-Contact" Tools for AI Agents
If an agent is entering this codebase for the first time, it should run these 5 tools in order to achieve 80% understanding with 20% token cost:

1.  **`get_architecture_overview`**: Provides the high-level map. The agent learns the "neighborhoods" (communities).
2.  **`list_flows`**: Identifies the most critical execution paths. This tells the agent what parts of the code actually "matter" to the user.
3.  **`get_hub_nodes`**: Identifies the architectural hotspots. The agent now knows which files are the "main" files.
4.  **`get_knowledge_gaps`**: Instantly shows where the codebase is weak, untested, or isolated.
5.  **`semantic_search_nodes`**: The agent uses this to find the specific logic relevant to its current task.

---

## 3. Fused Workflows (Agent Level-Up)

Instead of running tools one-by-one, an advanced agent should "Fuse" tool outputs to gain deep context.

### Fusion 1: The "Contextual Deep-Dive" (Understanding a Feature)
**Formula:** `semantic_search` + `query_graph(callers_of)` + `get_affected_flows`
*   **Why:** Searching for "Auth" tells you *where* it is. Finding callers tells you *who* uses it. Affected flows tells you *what* business logic depends on it.
*   **Industry Grade:** This mirrors how senior architects think—they don't look at a function in isolation; they look at its upstream impact.

### Fusion 2: The "PR Safety Check" (Reviewing Changes)
**Formula:** `detect_changes` + `get_impact_radius` + `get_suggested_questions`
*   **Why:** `detect_changes` scores the risk. `get_impact_radius` finds the hidden "Blast Radius" in distant files. `get_suggested_questions` provides the "Self-Correction" logic for the agent to verify its own work.

### Fusion 3: The "Refactor Preview" (Large Scale Changes)
**Formula:** `refactor(rename)` + `get_bridge_nodes` + `get_knowledge_gaps`
*   **Why:** Before renaming a symbol, the agent checks if that symbol is a "Bridge" (a chokepoint). If it is a bridge *and* has knowledge gaps (no tests), the agent knows the refactor is **High Risk**.

---

## 4. Scalability & Agent Efficiency

*   **Token Efficiency:** Using `get_review_context` instead of `read_file` on 10 files saves ~90% of the token budget. Agents that use the graph tools are "cheaper" to run and faster to respond.
*   **Context Management:** Instead of shoving 10,000 lines of code into the agent's memory, these tools allow the agent to keep a "Mental Map" of IDs and relationships, only pulling source code snippets when absolutely necessary.
*   **Language Agnostic:** Because the graph normalizes everything, the agent can understand a cross-language flow (e.g., Python calling a Rust binary) without needing to be an expert in both languages simultaneously.
