# Add CLI Commands for All MCP Tools

## Objective
Expose all available MCP tools as distinct, individual subcommands within the `code-review-graph` CLI, allowing users to invoke any graph analysis tool directly from the terminal.

## Key Files & Context
- `code_review_graph/cli.py`: The main entry point where `argparse` subcommands are defined and dispatched.
- `code_review_graph/tools/__init__.py`: Exports the ~28 available tool functions.
- `code_review_graph/tools/*`: The underlying implementations of the tools.

## Implementation Steps

1. **Identify Missing Subcommands**
   - Review all exported tools in `code_review_graph/tools/__init__.py`.
   - Map each tool to its required arguments (positional vs optional).

2. **Add Subcommands to `cli.py`**
   - For each missing tool, add a new subparser block.
   - Convert Python snake_case function names to CLI kebab-case command names (e.g., `get_impact_radius` -> `get-impact-radius`).
   - Add help text based on the tool's docstring.

3. **Dispatch Logic**
   - In the `main()` function of `cli.py`, add `if args.command == "tool-name":` blocks.
   - Inside each block, extract the arguments, call the corresponding function from `code_review_graph.tools`.
   - Use `asyncio.run()` for asynchronous tools (like `detect_changes` or `build_or_update_graph`).

4. **Formatting Output**
   - Print the results to stdout.
   - Use `json.dumps(result, indent=2)` for structured data to ensure it is machine-readable and human-friendly.

## Verification & Testing
1. **CLI Help:** Run `code-review-graph --help` to verify all new commands are listed.
2. **Command Execution:** Run a sample of the new commands (e.g., `code-review-graph status`) to ensure they successfully invoke the underlying function.
3. **Unit Tests:** Update `tests/test_cli.py` to ensure the new subcommands parse arguments correctly.
