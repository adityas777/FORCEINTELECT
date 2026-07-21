import argparse
import sys
import os
from retriever import parse_markdown_schema, SchemaRetriever

def main():
    parser = argparse.ArgumentParser(description="Text-to-SQL Table Retrieval CLI")
    parser.add_argument("query", type=str, help="Natural language query")
    parser.add_argument("--schema", type=str, default="schema_design.md", help="Path to schema Markdown file")
    args = parser.parse_args()

    if not os.path.exists(args.schema):
        print(f"Error: Schema file '{args.schema}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(args.schema, "r", encoding="utf-8") as f:
        md_content = f.read()

    try:
        tables = parse_markdown_schema(md_content)
        retriever = SchemaRetriever(tables)
        results = retriever.search(args.query)
        for name, _ in results:
            print(name)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
