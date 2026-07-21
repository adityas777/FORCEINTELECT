# SchemaScout: Text-to-SQL Table Retrieval System

SchemaScout is a local, reproducible stage-1 Text-to-SQL table retrieval system. It takes natural language questions and ranks the database tables by relevance. It operates **entirely offline** using local open-source retrieval methods, with **no external cloud LLM APIs**.

## 🚀 Key Features

1. **Hybrid Retrieval**: Integrates exact keyword search (**BM25**) with semantic vector search (**SentenceTransformers**) using a local `all-MiniLM-L6-v2` model.
2. **Schema-Aware FK Graph Expansion**: Builds a schema graph using **NetworkX** and traverses foreign-key relationships. It identifies shortest paths between high-matching seed tables to automatically pull in intermediate join tables (e.g. mapping `customer` and `product` to also fetch order tables).
3. **Advanced Preprocessing**: Automatically tokenizes, splits, and expands database table names and column abbreviations (e.g. `tbl_ord_hdr` ➡️ `table`, `order`, `header`) to bridge the vocabulary gap.
4. **FastAPI Web App & UI**: Features a beautiful glassmorphism web interface where users can type natural language queries and visualize matching scores, tables, and column metadata. It also supports uploading custom Markdown or JSON schemas dynamically.

---

## 🛠️ Installation & Setup

Ensure you have **Python 3.8+** installed. Then, follow these steps:

1. Clone or download this project workspace.
2. Open a terminal in the project directory.
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Usage

### 1. CLI Entrypoint
You can query the table retrieval system directly from your command line:
```bash
python cli.py "Show all products sold by seller 'TechZone'"
```
*Output (only table names, one per line):*
```text
product
seller_mst
```

To run against a custom schema Markdown file:
```bash
python cli.py "Find customers who registered recently" --schema my_custom_schema.md
```

### 2. Live Demo Web Application
Start the FastAPI server:
```bash
python app.py
```
Then open your browser and navigate to **[http://127.0.0.1:8000](http://127.0.0.1:8000)**.
You will see a modern dark-themed glassmorphism interface supporting:
- Interactive text box queries.
- Expandable results displaying table descriptions and color-coded Primary/Foreign key column badges.
- Custom schema file uploader (drag & drop JSON/Markdown).

### 3. Run Evaluation Prompts
To run all 10 evaluation prompts and output their results:
```bash
python eval.py
```
This prints the ranked table listings for each prompt and saves them to `evaluation_results.txt`.

---

## 🧠 Architectural Overview & Design Choices

### A. Preprocessing & Expansion
To allow standard lexical (BM25) and dense embeddings to match developer-written table/column names, we perform programmatic expansion. For instance:
- `pay_trn` is expanded to: `pay trn payment transaction`
- Column names are indexed alongside their expanded versions to maximize similarity.
- For the default e-commerce schema, common synonyms (e.g., matching `payout` and `payback` to `rfnd_log` and `return_req`) are appended to table documents.

### B. Hybrid Scoring
Sparse and dense retrievals capture different relevance aspects:
- **Sparse (BM25)** matches precise names and keywords.
- **Dense (SentenceTransformers)** matches semantic intent (e.g. mapping "checkout" to `tbl_ord_hdr`).
Scores are normalized and linearly combined using a weighted sum:
$$\text{Score} = 0.55 \times \text{Dense} + 0.45 \times \text{BM25}$$

### C. Foreign Key Graph Completion
Typical vector searches are blind to database schema structures. If a query requests "refunds for returned products by customer", vector search may return `rfnd_log`, `return_req`, and `customer` but miss `tbl_ord_hdr` and `tbl_ord_item` which are required to perform the joins.
SchemaScout:
1. Treats high-scoring tables as "seeds".
2. Constructs a NetworkX schema graph where edges are foreign key relationships.
3. Computes shortest paths between all pairs of seed tables.
4. Boosts and includes any intermediate tables on paths $\le 3$ hops to guarantee joinability.

### D. Thresholding
Any tables scoring below `0.18` (after boost) are discarded to avoid returning unrelated tables. If no tables exceed the threshold, the single top-matching table is returned as a fallback.
