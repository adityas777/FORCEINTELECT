import os
import sys

# Reconfigure stdout to support UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from retriever import parse_markdown_schema, SchemaRetriever

GENERALIZATION_QUERIES = [
    {
        "id": 1,
        "query": "Find all delivery addresses of customers living in New York.",
        "rationale": "Needs cust_addr (addresses) and customer (profile details)."
    },
    {
        "id": 2,
        "query": "Identify which sellers are currently offering discount coupons.",
        "rationale": "Needs seller_mst (seller profile) and coupon (discounts/promo codes)."
    },
    {
        "id": 3,
        "query": "Show reviews submitted by customers for products in the 'Electronics' category.",
        "rationale": "Needs review, customer, product, and category."
    },
    {
        "id": 4,
        "query": "Check the shipping tracking number and carrier name for shipment of order number 10045.",
        "rationale": "Needs ship_hdr (carrier/tracking) and tbl_ord_hdr (orders)."
    },
    {
        "id": 5,
        "query": "List products and their categories recommended to customers who recently browsed them.",
        "rationale": "Needs product, category, recommendation_log, recently_viewed, and customer."
    },
    {
        "id": 6,
        "query": "Calculate the total refund amount processed for transactions paid by credit card.",
        "rationale": "Needs rfnd_log (refund amount) and pay_trn (payment method/card)."
    },
    {
        "id": 7,
        "query": "Get the list of products currently stored in the 'Seattle Main' warehouse.",
        "rationale": "Needs product, inv_stock, and warehouse (specific warehouse storage)."
    },
    {
        "id": 8,
        "query": "Find items currently added to shopping carts by customers.",
        "rationale": "Needs cart_item (shopping carts) and customer."
    },
    {
        "id": 9,
        "query": "Retrieve the details of return requests that are currently pending approval.",
        "rationale": "Needs return_req (return details) and potentially tbl_ord_item or customer."
    },
    {
        "id": 10,
        "query": "List all coupons applied to orders placed last month.",
        "rationale": "Needs coupon (discounts) and tbl_ord_hdr (placed orders)."
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

    print("=" * 60)
    print("RUNNING GENERALIZATION VALIDATION (10 UNSEEN QUERIES)")
    print("=" * 60)

    for case in GENERALIZATION_QUERIES:
        print(f"\n[Query #{case['id']}]: \"{case['query']}\"")
        print(f"Rationale: {case['rationale']}")
        
        results = retriever.search(case['query'])
        actual = [name for name, _ in results]
        print(f"Retrieved: {actual}")
        print("-" * 60)

if __name__ == "__main__":
    main()
