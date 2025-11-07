## Repo snapshot

- **Main entry**: `main.py` — CLI that scans `*.sql` files, auto-detects dialects (trino, duckdb, ansi), extracts table dependencies via `sqlglot`, and outputs Mermaid diagrams + dialect summary.
- **Dependency**: `sqlglot>=27.29.0` (in `pyproject.toml`). Python >= 3.9.
- **No tests yet**: create `tests/` folder targeting `extract_dependencies` when adding test coverage.

## Key functions & architecture

- **`auto_detect_parse(sql_text)`**: tries dialects in order (trino → duckdb → ansi). Returns `(parsed_statements, dialect)` or `([], None)` if unparseable.
- **`fully_qualified_table_name(table_expr)`**: extracts catalog.schema.table (or schema.table or table) from sqlglot `Table` node. Preserves all available name parts.
- **`extract_dependencies(sql_text)`**: finds input tables via `stmt.find_all(exp.Table)` and output tables from `Create`/`Insert` targets. Returns `(input_set, output_set, dialect)`.
- **`build_dependency_graph(sql_dir)`**: scans `*.sql` files recursively, builds `{output_table: [input_tables]}` and file metadata.
- **`build_script_dependencies(file_metadata)`**: creates script-level graph where `{script_B: [script_A]}` means A outputs what B reads.
- **`generate_mermaid(graph)`**: converts dependency dict to Mermaid `graph TD` format.

## Usage & outputs

```bash
python main.py --sql-dir ./sql_scripts [--out-prefix dependencies]
```

**Default outputs**:

- `dependencies_tables.mmd` — table-level dependency graph
- `dependencies_scripts.mmd` — script-level execution order graph
- `dependencies_dialects.txt` — per-file detected dialect summary

## Conventions & patterns

- **SQL discovery**: uses `Path.rglob("*.sql")` to find files recursively.
- **Table naming**: `fully_qualified_table_name` preserves catalog.schema.table structure from sqlglot AST. No quote stripping or normalization beyond what sqlglot provides.
- **Dialect detection order**: more-specific dialects first (trino, duckdb, ansi). Add new dialects to `auto_detect_parse` list in priority order.
- **Graph structure**:
  - `table_graph` = `{output_table: [input_tables]}`
  - `script_graph` = `{downstream_script: [upstream_scripts]}`

## Error modes

- **Unparseable SQL**: `extract_dependencies` warns and returns empty sets; dialect = `unknown`.
- **Missed outputs**: only `CREATE` and `INSERT` targets are detected as outputs. Other DDL (e.g., `ALTER`, `MERGE`) may be missed.

## Dev hints

- **Testing**: create `tests/` with minimal SQL examples exercising `CREATE`, `INSERT`, `JOIN`, subqueries. Target `extract_dependencies` and `fully_qualified_table_name`.
- **Performance**: current code reads full files via `Path.read_text()`. Fine for small-to-medium repos; consider streaming for large datasets.
- **Output changes**: if modifying filenames or graph directions, update both generation and CLI print messages in `main()`.
