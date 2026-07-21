import os
import sys
import numpy as np

from retriever import parse_markdown_schema, SchemaRetriever

def main():
    schema_path = "schema_design.md"
    if not os.path.exists(schema_path):
        print(f"Error: {schema_path} not found.")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        md_content = f.read()

    tables = parse_markdown_schema(md_content)
    retriever = SchemaRetriever(tables)

    queries = [
        "Find customers who have saved products to their wishlist.",
        "Find customers who added products to their cart but later purchased the same products."
    ]

    for q in queries:
        print(f"==================================================")
        print(f"Query: \"{q}\"")
        print(f"--------------------------------------------------")
        # 1. BM25 score
        tokenized_query = retriever._tokenize(q)
        bm25_scores = np.array(retriever.bm25.get_scores(tokenized_query))
        if len(bm25_scores) > 0 and (max(bm25_scores) - min(bm25_scores)) > 1e-9:
            bm25_scores = (bm25_scores - min(bm25_scores)) / (max(bm25_scores) - min(bm25_scores))
        else:
            bm25_scores = np.zeros_like(bm25_scores)
            
        # 2. Dense score
        query_emb = retriever.model.encode(q, convert_to_tensor=False)
        query_emb = np.array(query_emb)
        norm_query = np.linalg.norm(query_emb)
        norm_docs = np.linalg.norm(retriever.doc_embeddings, axis=1)
        dense_scores = np.dot(retriever.doc_embeddings, query_emb) / (norm_docs * norm_query + 1e-9)
        if len(dense_scores) > 0 and (max(dense_scores) - min(dense_scores)) > 1e-9:
            dense_scores = (dense_scores - min(dense_scores)) / (max(dense_scores) - min(dense_scores))
        else:
            dense_scores = np.zeros_like(dense_scores)
            
        combined_scores = 0.55 * dense_scores + 0.45 * bm25_scores
        table_scores = {retriever.table_names[i]: combined_scores[i] for i in range(len(retriever.table_names))}
        
        ranked = sorted(table_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (name, score) in enumerate(ranked, 1):
            print(f"{rank:2d}. {name:<20} : {score:.4f}")
            
    print("==================================================")

if __name__ == "__main__":
    main()
