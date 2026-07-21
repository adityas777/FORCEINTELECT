import os
import sys
import re

# Reconfigure stdout to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from retriever import parse_markdown_schema, SchemaRetriever

SAMPLE_TEST_CASES = [
    {
        "query": "Show customers who have placed orders but have not completed payment.",
        "expected": {"pay_trn", "tbl_ord_hdr", "customer"}
    },
    {
        "query": "Find products that are currently out of stock.",
        "expected": {"inv_stock", "product", "warehouse"}
    },
    {
        "query": "List customers who purchased products but never submitted a review.",
        "expected": {"review", "tbl_ord_item", "tbl_ord_hdr", "customer", "product"}
    }
]

def main():
    schema_path = "schema_design.md"
    if not os.path.exists(schema_path):
        print(f"Error: {schema_path} not found.")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    tables = parse_markdown_schema(md_content)
    retriever = SchemaRetriever(tables)

    print("Running sanity tests on samples...\n")
    for case in SAMPLE_TEST_CASES:
        print(f"Query: \"{case['query']}\"")
        print(f"Expected: {sorted(list(case['expected']))}")
        
        # Test search
        results = retriever.search(case['query'])
        actual = [name for name, _ in results]
        print(f"Actual:   {actual}")
        
        # Check intersection & matches
        missing = case['expected'] - set(actual)
        extra = set(actual) - case['expected']
        
        if not missing and not extra:
            print("Status: PERFECT MATCH")
        else:
            if missing:
                print(f"Status: MISSING tables: {missing}")
            if extra:
                print(f"Status: EXTRA tables: {extra}")
        print("-" * 50)

if __name__ == "__main__":
    main()
