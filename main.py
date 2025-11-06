"""
main.py
Analyze SQL dependencies across multiple .sql scripts (mixed dialects)
and output:
  1. dependencies_tables.mmd  - table-level dependencies
  2. dependencies_scripts.mmd - script-level (execution order) dependencies
  3. dialect_summary.txt      - which SQL file was parsed as which dialect

Usage:
    python main.py --sql-dir ./sql_scripts
"""

import argparse
from pathlib import Path
import sqlglot
from sqlglot import expressions as exp


# ---------------------------
# Helper: auto-detect dialect
# ---------------------------
def auto_detect_parse(sql_text: str):
    """
    Try parsing SQL in order: trino -> duckdb -> ansi
    Returns (parsed_statements, detected_dialect)
    """
    for dialect in ["trino", "duckdb", "ansi"]:
        try:
            parsed = sqlglot.parse(sql_text, read=dialect)
            return parsed, dialect
        except Exception:
            continue
    return [], None


# ---------------------------
# Extract dependencies from SQL
# ---------------------------
def extract_dependencies(sql_text: str):
    input_tables = set()
    output_tables = set()

    parsed_statements, dialect = auto_detect_parse(sql_text)

    if not parsed_statements:
        print("[WARN] Could not parse SQL under Trino/DuckDB/ANSI.")
        return input_tables, output_tables, None

    for stmt in parsed_statements:
        # Extract all tables used in FROM, JOIN, etc.
        for table in stmt.find_all(exp.Table):
            table_name = table.sql(dialect="ansi").strip('"')
            input_tables.add(table_name)

        # Detect CREATE TABLE / INSERT INTO targets
        if isinstance(stmt, exp.Create):
            output_tables.add(stmt.this.sql(dialect="ansi"))
        elif isinstance(stmt, exp.Insert):
            output_tables.add(stmt.this.sql(dialect="ansi"))

    return input_tables, output_tables, dialect


# ---------------------------
# Build dependency graphs
# ---------------------------
def build_dependency_graph(sql_dir: Path):
    """
    Builds:
    - table_graph: {output_table: [input_tables]}
    - file_metadata: {file_name: {"inputs": [], "outputs": [], "dialect": str}}
    """
    table_graph = {}
    file_metadata = {}

    for sql_file in sql_dir.rglob("*.sql"):
        sql_text = sql_file.read_text(encoding="utf-8")
        inputs, outputs, dialect = extract_dependencies(sql_text)

        file_metadata[sql_file.name] = {
            "inputs": list(inputs),
            "outputs": list(outputs),
            "dialect": dialect or "unknown",
        }

        for out_tbl in outputs:
            table_graph[out_tbl] = list(inputs)

    return table_graph, file_metadata


# ---------------------------
# Build script-level dependencies
# ---------------------------
def build_script_dependencies(file_metadata):
    """
    Determine which scripts depend on others.
    Script A → Script B if A outputs a table that B reads.
    Returns {script_B: [script_A]}
    """
    table_to_script = {}
    for script, meta in file_metadata.items():
        for t in meta["outputs"]:
            table_to_script[t] = script

    script_graph = {}

    for script, meta in file_metadata.items():
        upstream_scripts = set()
        for input_tbl in meta["inputs"]:
            if input_tbl in table_to_script:
                upstream_scripts.add(table_to_script[input_tbl])
        if upstream_scripts:
            script_graph[script] = list(upstream_scripts)

    return script_graph


# ---------------------------
# Mermaid Diagram Generator
# ---------------------------
def generate_mermaid(graph: dict, label: str = "graph TD") -> str:
    lines = [label]
    for target, sources in graph.items():
        for src in sources:
            if src != target:
                lines.append(f"  {src} --> {target}")
    return "\n".join(lines)


# ---------------------------
# Save dialect summary
# ---------------------------
def save_dialect_summary(file_metadata, out_path: Path):
    lines = ["Detected SQL dialects per file:\n"]
    for file, meta in file_metadata.items():
        lines.append(f"{file:<40} : {meta['dialect']}")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n🧠 Dialect summary saved to: {out_path}")


# ---------------------------
# Main CLI Entry
# ---------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Analyze SQL dependencies and output Mermaid diagrams."
    )
    parser.add_argument(
        "--sql-dir", required=True, help="Path to folder containing .sql scripts"
    )
    parser.add_argument(
        "--out-prefix", default="dependencies", help="Output prefix for .mmd files"
    )
    args = parser.parse_args()

    sql_dir = Path(args.sql_dir)
    if not sql_dir.exists():
        raise FileNotFoundError(f"SQL directory not found: {sql_dir}")

    print(f"\n📂 Scanning SQL folder: {sql_dir}")

    # Step 1. Parse and detect dialects
    table_graph, file_metadata = build_dependency_graph(sql_dir)

    # Step 2. Script-level dependencies
    script_graph = build_script_dependencies(file_metadata)

    # Step 3. Print summary
    print("\n📊 Table-level dependencies:")
    for tgt, srcs in table_graph.items():
        print(f"  {tgt} <- {srcs}")

    print("\n🧩 Script-level dependencies (execution order):")
    for script, upstreams in script_graph.items():
        print(f"  {script} <- {upstreams}")

    print("\n🧠 Dialects detected:")
    for file, meta in file_metadata.items():
        print(f"  {file:<40} : {meta['dialect']}")

    # Step 4. Output Mermaid + Dialect files
    out_table = Path(f"{args.out_prefix}_tables.mmd")
    out_script = Path(f"{args.out_prefix}_scripts.mmd")
    out_dialect = Path(f"{args.out_prefix}_dialects.txt")

    out_table.write_text(generate_mermaid(table_graph), encoding="utf-8")
    out_script.write_text(generate_mermaid(script_graph), encoding="utf-8")
    save_dialect_summary(file_metadata, out_dialect)

    print(f"\n✅ Mermaid diagrams saved:")
    print(f"   • {out_table}")
    print(f"   • {out_script}")
    print(f"\nPreview in VSCode Mermaid plugin or https://mermaid.live/\n")


if __name__ == "__main__":
    main()
