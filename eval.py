import os
from retriever import parse_markdown_schema, SchemaRetriever

PROMPTS = [
    "Show all products sold by seller \"TechZone\".",
    "List all orders where a coupon was applied during checkout.",
    "Find customers who have saved products to their wishlist.",
    "Show products that customers returned after they had already been delivered.",
    "Find customers who received refunds for returned products.",
    "List sellers whose products have received reviews with ratings below 2.",
    "Find customers who added products to their cart but later purchased the same products.",
    "Identify products that were returned, refunded, and later purchased again by the same customer.",
    "Find customers who purchased products from different sellers, received shipments from multiple warehouses, returned at least one item, and whose refund has not yet been processed.",
    "Identify customers who viewed a product multiple times, added it to their wishlist, later purchased it using a coupon, submitted a low-rated review, returned the product, but have not yet received a refund."
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

    print("Running evaluation prompts...\n")
    
    with open("evaluation_results.txt", "w", encoding="utf-8") as out:
        for idx, prompt in enumerate(PROMPTS, 1):
            print(f"--- Prompt {idx}: {prompt} ---")
            out.write(f"--- Prompt {idx}: {prompt} ---\n")
            
            results = retriever.search(prompt)
            ranked_names = [name for name, _ in results]
            
            for name in ranked_names:
                print(name)
                out.write(name + "\n")
            print()
            out.write("\n")
            
    print("Results saved to evaluation_results.txt")

if __name__ == "__main__":
    main()
