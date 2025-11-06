## Repo snapshot

- Main entry: `main.py` — a small CLI that scans a directory of `*.sql` files, auto-detects dialects (trino, duckdb, ansi), extracts input/output tables using `sqlglot`, and writes two Mermaid diagrams plus a dialect summary.
- Dependency: `sqlglot>=27.29.0` (declared in `pyproject.toml`). Python requires >= 3.9.

## What a coding agent should know (concise)

- Purpose: infer table-level and script-level dependencies across a collection of SQL scripts and emit Mermaid-compatible `.mmd` files plus a `*_dialects.txt` summary.
- Key file: `main.py`. Important functions to read first: `auto_detect_parse`, `extract_dependencies`, `build_dependency_graph`, `build_script_dependencies`, and `generate_mermaid`.
- Dialect detection: `auto_detect_parse(sql_text)` tries `trino`, then `duckdb`, then `ansi`. If none parse, the SQL is considered unparsed and the code returns an empty parse with a printed warning.
- Table extraction: code looks for `sqlglot.expressions.Table` nodes (via `stmt.find_all(exp.Table)`) for inputs and `Create` / `Insert` expressions for outputs. Output table names are emitted using `stmt.this.sql(dialect="ansi")`.

## Quick examples (from repo)

- Run the CLI against a folder of SQL: `python main.py --sql-dir ./sql_scripts`
- Default outputs (when `--out-prefix dependencies`):
  - `dependencies_tables.mmd` — table-level graph
  - `dependencies_scripts.mmd` — script-level (execution order) graph
  - `dependencies_dialects.txt` — per-file detected dialects

## Conventions & patterns to follow

- SQL discovery: the code uses `Path.rglob("*.sql")` to find files; keep SQL files under a discoverable folder when adding tests or fixtures.
- Table identity: identifiers are normalized by calling `table.sql(dialect="ansi")` and stripping quotes. Be careful when adding schema-aware logic — current code preserves whatever `sqlglot` produces for the `ansi` dialect.
- Dialect list: if you add support for another dialect (e.g., `postgres`), update `auto_detect_parse` and keep the detection order intentional (more-specific dialects first).
- Graph shapes: `table_graph` keys are output tables and values are lists of input tables. `script_graph` maps a script to upstream scripts (A → B if A outputs something B reads).

## Error modes & expectations

- Unparseable SQL: `extract_dependencies` prints a warning and returns empty input/output sets; the file's dialect will be `unknown` in the dialect summary.
- Ambiguous outputs: the code treats `CREATE` and `INSERT` targets as outputs. If a script mutates tables via DDL not represented as `Create`/`Insert`, it may be missed.

## Helpful hints for contributors/agents

- When editing parsing logic, add small unit tests (create a `tests/` folder) with minimal SQL examples that exercise `Create`, `Insert`, `JOIN`, and subqueries. Tests are not present in the repo—create lightweight ones targeting `extract_dependencies`.
- If you change output filenames or graph directions, update both places in `main.py` (generation and printing) so the CLI messages remain accurate.
- For performance with many SQL files, prefer streaming reads and incremental graph updates; the current code reads whole files into memory via `Path.read_text()` which is fine for small-to-medium repos.

## Where to look next in the codebase

- `main.py` — primary logic and CLI
- `pyproject.toml` — runtime dependency (`sqlglot`) and Python version

If you want the file adjusted (different tone, more/less detail, add examples or tests), tell me what to expand or remove and I will iterate.
