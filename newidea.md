# Text-to-SQL Table Retrieval System — Build Spec

## 1. Objective

Build a local, reproducible system that takes a **natural language question** and the
**e-commerce database schema** below, and returns a **ranked list of relevant table names**
(most relevant → least relevant). This is *only* the table-retrieval stage of a Text-to-SQL
pipeline — **do not generate SQL**.

## 2. Hard Constraints

- **No hosted/cloud LLM APIs of any kind** (OpenAI, Anthropic, Gemini, Groq, OpenRouter,
  Azure OpenAI, Cohere, Mistral API, etc.) — strictly prohibited.
- Local embedding models, classic IR (BM25, TF-IDF), vector search, hybrid search, graph
  traversal over FK relationships, metadata engineering, and local reranking are all allowed.
- Any programming language / open-source library is fine (Python recommended: `rank_bm25`,
  `sentence-transformers`, `faiss`/`chromadb`/`sqlite`, `networkx`, etc. — all run locally,
  no API keys).
- Must **not hardcode** answers to the sample/eval prompts. Must generalize to unseen NL
  queries over this schema.
- Output for each query: **only table names, one per line, ranked most→least relevant**, no
  explanations, no scores, no extra text. Return only tables that are actually necessary
  (no fixed count — but don't return unnecessary tables, that's penalized).
- Solution must run fully offline/locally and be reproducible from a fresh clone
  (`requirements.txt` + clear run instructions).

## 3. Database Schema (E-Commerce)

> Preprocess this into whatever internal representation helps retrieval (e.g., one "document"
> per table combining its name, description, column names, and FK relationships — this is
> exactly the kind of metadata engineering the assignment allows/encourages).

### customer
Stores registered customers and their account information.
| Column | PK | FK → |
|---|---|---|
| customer_id | ✅ | |
| cust_code | | |
| full_name | | |
| email | | |
| phone | | |
| status | | |
| created_at | | |

### cust_addr
Stores customer shipping and billing addresses.
| Column | PK | FK → |
|---|---|---|
| addr_id | ✅ | |
| customer_id | | customer.customer_id |
| addr_type | | |
| line1 | | |
| city | | |
| state | | |
| postal_cd | | |
| is_default | | |

### seller_mst
Stores marketplace sellers.
| Column | PK | FK → |
|---|---|---|
| seller_id | ✅ | |
| seller_nm | | |
| email | | |
| rating | | |
| is_active | | |

### category
Product categories (self-referencing for parent/child).
| Column | PK | FK → |
|---|---|---|
| category_id | ✅ | |
| category_name | | |
| parent_category_id | | category.category_id |

### product
Master list of products sold on the platform.
| Column | PK | FK → |
|---|---|---|
| product_id | ✅ | |
| category_id | | category.category_id |
| seller_id | | seller_mst.seller_id |
| sku | | |
| product_name | | |
| brand | | |
| is_active | | |

### inv_stock
Current inventory available in warehouses.
| Column | PK | FK → |
|---|---|---|
| stock_id | ✅ | |
| product_id | | product.product_id |
| warehouse_id | | warehouse.warehouse_id |
| qty_available | | |
| reserved_qty | | |
| last_upd | | |

### warehouse
Warehouses storing inventory.
| Column | PK | FK → |
|---|---|---|
| warehouse_id | ✅ | |
| warehouse_name | | |
| city | | |
| state | | |

### tbl_ord_hdr
Customer order header.
| Column | PK | FK → |
|---|---|---|
| ord_id | ✅ | |
| customer_id | | customer.customer_id |
| order_date | | |
| sts_cd | | |
| coupon_id | | coupon.coupon_id |
| ship_addr_id | | cust_addr.addr_id |
| total_amount | | |

### tbl_ord_item
Products belonging to an order.
| Column | PK | FK → |
|---|---|---|
| ord_item_id | ✅ | |
| ord_id | | tbl_ord_hdr.ord_id |
| product_id | | product.product_id |
| qty | | |
| unit_price | | |
| discount_amt | | |

### pay_trn
Payment transactions for customer orders.
| Column | PK | FK → |
|---|---|---|
| payment_id | ✅ | |
| ord_id | | tbl_ord_hdr.ord_id |
| payment_method | | |
| payment_status | | |
| txn_ref | | |
| paid_amt | | |
| paid_on | | |

### ship_hdr
Shipment details.
| Column | PK | FK → |
|---|---|---|
| shipment_id | ✅ | |
| ord_id | | tbl_ord_hdr.ord_id |
| warehouse_id | | warehouse.warehouse_id |
| carrier | | |
| tracking_no | | |
| shipped_date | | |
| delivery_status | | |

### return_req
Customer return requests.
| Column | PK | FK → |
|---|---|---|
| return_id | ✅ | |
| ord_item_id | | tbl_ord_item.ord_item_id |
| reason | | |
| request_date | | |
| return_status | | |

### rfnd_log
Refund processing records.
| Column | PK | FK → |
|---|---|---|
| refund_id | ✅ | |
| return_id | | return_req.return_id |
| payment_id | | pay_trn.payment_id |
| refund_amt | | |
| refund_status | | |
| processed_on | | |

### coupon
Coupons available to customers.
| Column | PK | FK → |
|---|---|---|
| coupon_id | ✅ | |
| coupon_code | | |
| discount_type | | |
| discount_value | | |
| valid_from | | |
| valid_to | | |

### review
Customer product reviews.
| Column | PK | FK → |
|---|---|---|
| review_id | ✅ | |
| product_id | | product.product_id |
| customer_id | | customer.customer_id |
| rating | | |
| review_text | | |
| reviewed_on | | |

### cart_item
Products currently in a customer's cart, not yet purchased.
| Column | PK | FK → |
|---|---|---|
| cart_item_id | ✅ | |
| customer_id | | customer.customer_id |
| product_id | | product.product_id |
| qty | | |
| added_at | | |

### wishlist_item
Products customers have saved for future purchase.
| Column | PK | FK → |
|---|---|---|
| wishlist_id | ✅ | |
| customer_id | | customer.customer_id |
| product_id | | product.product_id |
| created_at | | |

### recently_viewed
Tracks products viewed by customers.
| Column | PK | FK → |
|---|---|---|
| view_id | ✅ | |
| customer_id | | customer.customer_id |
| product_id | | product.product_id |
| viewed_at | | |

### recommendation_log
Products recommended by the recommendation engine.
| Column | PK | FK → |
|---|---|---|
| rec_id | ✅ | |
| customer_id | | customer.customer_id |
| product_id | | product.product_id |
| algo_name | | |
| score | | |
| generated_at | | |

## 4. Given Sample Test Cases (for sanity-checking only — do NOT hardcode)

1. **"Show customers who have placed orders but have not completed payment."**
   → `pay_trn`, `tbl_ord_hdr`, `customer`
2. **"Find products that are currently out of stock."**
   → `inv_stock`, `product`, `warehouse`
3. **"List customers who purchased products but never submitted a review."**
   → `review`, `tbl_ord_item`, `tbl_ord_hdr`, `customer`, `product`

## 5. Evaluation Prompts to Run (paste your ranked output for each into the assignment form)

1. Show all products sold by seller "TechZone".
2. List all orders where a coupon was applied during checkout.
3. Find customers who have saved products to their wishlist.
4. Show products that customers returned after they had already been delivered.
5. Find customers who received refunds for returned products.
6. List sellers whose products have received reviews with ratings below 2.
7. Find customers who added products to their cart but later purchased the same products.
8. Identify products that were returned, refunded, and later purchased again by the same customer.
9. Find customers who purchased products from different sellers, received shipments from multiple warehouses, returned at least one item, and whose refund has not yet been processed.
10. Identify customers who viewed a product multiple times, added it to their wishlist, later purchased it using a coupon, submitted a low-rated review, returned the product, but have not yet received a refund.

## 6. Suggested Implementation Approach (recommended, adjust as needed)

1. **Schema preprocessing**: For each table, build a text "document" = table name +
   description + column names (+ flagged PK/FK) + any business synonyms
   (e.g. `pay_trn` → "payment transaction", `tbl_ord_hdr` → "order header").
2. **Hybrid retrieval**:
   - Sparse: BM25 over the table documents (`rank_bm25`).
   - Dense: local sentence-transformer embeddings (e.g. `all-MiniLM-L6-v2`) + cosine
     similarity, computed with `sentence-transformers` (no API calls — model runs locally).
   - Combine scores (e.g. weighted sum or reciprocal rank fusion).
3. **Graph expansion**: Build a FK graph (`networkx`) of the schema. After getting top
   seed tables from hybrid retrieval, expand along FK edges 1 hop to pull in join-critical
   tables that a keyword match might miss (e.g. query mentions "refund" → pull in
   `rfnd_log`, `return_req`, `pay_trn` since they're FK-chained).
   This matters a lot for the multi-hop prompts (7–10).
4. **Reranking**: Optionally rerank the candidate set with a local cross-encoder
   (`cross-encoder/ms-marco-MiniLM-L-6-v2`) for better ordering, still no API calls.
5. **Thresholding**: Drop low-score tables below a cutoff so unrelated tables aren't
   returned (avoids the "returning unnecessary tables" penalty).
6. **Output formatting**: print one table name per line, most→least relevant, nothing else.

## 7. Optional Enhancement — Live Demo Web App

> This is a **bonus on top of the required deliverables**, not a replacement for them. The
> assignment still requires the solution to run and be reproducible fully locally — the
> hosted demo just makes it easier for an evaluator to try their own queries without cloning
> the repo first.

### 7.1 Goal

Deploy a small, live web app where a user can:
1. Type any natural language query (e.g. *"Identify customers who viewed a product multiple
   times, added it to their wishlist, later purchased it using a coupon, submitted a
   low-rated review, returned the product, but have not yet received a refund"*).
2. Get back the ranked list of relevant tables, computed against the **default e-commerce
   schema** (Section 3) — same retrieval pipeline as the local CLI, just wrapped in an API.
3. Optionally **upload their own schema** (JSON/YAML/Markdown — pick one format and document
   it clearly) and have all subsequent queries in that session run against the uploaded
   schema instead of the default one.

### 7.2 Suggested Architecture

- **Backend**: FastAPI (or Flask) exposing:
  - `POST /query` — body: `{ "question": str, "schema_id": str (optional) }` → returns
    ranked table names as JSON (and this is also what the UI renders).
  - `POST /schema/upload` — accepts a schema file, validates + parses it into the same
    internal table-document representation used for the default schema, stores it
    (in-memory or a temp store keyed by a session/schema id), and returns a `schema_id` to
    use in subsequent `/query` calls.
  - `GET /schema/default` — returns the built-in e-commerce schema so the UI can show what's
    "currently loaded."
- **Retrieval core stays untouched**: the same BM25 + local embeddings + FK-graph-expansion
  pipeline from Section 6 should be schema-agnostic — it should already accept "a set of
  table documents + a FK graph" as input rather than hardcoding the e-commerce schema, so
  swapping in an uploaded schema is just swapping that input, not writing new logic.
- **Frontend**: a single simple page (plain HTML/JS, or Streamlit/Gradio if that's faster to
  ship) with:
  - A text box for the query + "Run" button → shows ranked table list.
  - A small indicator of which schema is active ("Default e-commerce schema" vs
    "Custom: <filename>").
  - An "Upload schema" button/file picker, with an example/template file linked so users know
    the expected format.
- **Hosting**: anything that runs your local models without paid inference (e.g. a small VM,
  Render/Railway free tier, HF Spaces, or a Docker container on your own host). Since no
  hosted LLM APIs are used anyway, this should be cheap/free to run.

### 7.3 Schema Upload Format (pick one and document it in your README)

Recommend the same table structure already used in Section 3, e.g. as JSON:

```json
{
  "tables": [
    {
      "name": "customer",
      "description": "Stores registered customers and their account information.",
      "columns": [
        {"name": "customer_id", "is_pk": true, "is_fk": false},
        {"name": "email", "is_pk": false, "is_fk": false}
      ]
    }
  ],
  "foreign_keys": [
    {"table": "cust_addr", "column": "customer_id", "ref_table": "customer", "ref_column": "customer_id"}
  ]
}
```

Parsing this into your existing internal "table document + FK graph" representation should
require no changes to the retrieval logic itself — just a new schema-loading function.

### 7.4 Notes / Trade-offs to mention in your summary

- Clarify that the hosted demo and the local CLI/script share the exact same retrieval code
  path (no duplicated logic) — this is what keeps the "must be reproducible locally"
  requirement satisfied even with a live version existing.
- If the uploaded schema is large, mention how you handle re-embedding/re-indexing cost
  (e.g. compute embeddings once on upload, cache per `schema_id`, not per query).
- Note any validation you do on uploaded schemas (missing required fields, malformed FK
  references, etc.) and how errors are surfaced to the user.

## 8. Deliverables Checklist

- [ ] `README.md` explaining setup + how to run.
- [ ] `requirements.txt` with pinned local-only dependencies.
- [ ] Source code (schema preprocessing, retrieval, ranking, CLI/script entrypoint that takes
      a query string and prints ranked table names).
- [ ] Script/notebook that runs all 10 evaluation prompts above and prints results.
- [ ] Push everything to a **public GitHub repo**.
- [ ] Write a **200–500 word summary** covering: overall retrieval approach, schema
      preprocessing, retrieval/ranking techniques used, and assumptions/trade-offs.
- [ ] Paste the ranked table-name output for each of the 10 prompts into the assignment
      answer fields (table names only, one per line).
- [ ] *(Optional, bonus)* Live demo link (Section 7) with query box + schema upload, and a
      one-line mention in your summary that it shares the same code as the local pipeline.
