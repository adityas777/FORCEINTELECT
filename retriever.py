import os
# Force HuggingFace to work entirely offline to prevent update checks and network hangs
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import re
import json
import numpy as np
import networkx as nx
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

class ColumnInfo:
    def __init__(self, name, is_pk=False, is_fk=False, ref_table=None, ref_col=None):
        self.name = name
        self.is_pk = is_pk
        self.is_fk = is_fk
        self.ref_table = ref_table if ref_table and ref_table.lower() != "null" else None
        self.ref_col = ref_col if ref_col and ref_col.lower() != "null" else None

    def to_dict(self):
        return {
            "name": self.name,
            "is_pk": self.is_pk,
            "is_fk": self.is_fk,
            "ref_table": self.ref_table,
            "ref_col": self.ref_col
        }

class TableSchema:
    def __init__(self, name, description="", columns=None):
        self.name = name
        self.description = description
        self.columns = columns if columns else []

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "columns": [c.to_dict() for c in self.columns]
        }

def expand_name(name):
    # Split by underscore or camelcase
    parts = re.split(r'[_]+', name)
    expansion = []
    abbrevs = {
        "tbl": "table",
        "ord": "order",
        "hdr": "header",
        "trn": "transaction",
        "mst": "master",
        "cust": "customer",
        "addr": "address",
        "inv": "inventory",
        "pay": "payment",
        "ship": "shipment",
        "rfnd": "refund",
        "req": "request",
        "sts": "status",
        "cd": "code",
        "nm": "name",
        "qty": "quantity",
        "amt": "amount",
        "ref": "reference",
        "txn": "transaction",
        "upd": "update",
        "rec": "recommendation",
        "algo": "algorithm",
        "pk": "primary key",
        "fk": "foreign key"
    }
    for p in parts:
        expansion.append(p)
        if p.lower() in abbrevs:
            expansion.append(abbrevs[p.lower()])
    return " ".join(expansion)

def parse_markdown_schema(md_content):
    # Split by markdown headers or ---
    sections = re.split(r'\n---\s*\n', md_content)
    tables = []
    
    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        lines = section.split('\n')
        table_name = None
        description_lines = []
        table_started = False
        columns = []
        
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            
            # Match table header: "# table_name" or "### table_name"
            header_match = re.match(r'^#+\s+(\w+)', line_str)
            if header_match:
                table_name = header_match.group(1).strip()
                continue
            
            # Match column table header/separator
            if line_str.startswith('|') and ('Column' in line_str or '---' in line_str or 'is_pk' in line_str):
                table_started = True
                continue
            
            if table_started:
                # Parse column row
                if line_str.startswith('|') and line_str.endswith('|'):
                    # Strip outer pipes and split
                    parts = [p.strip() for p in line_str[1:-1].split('|')]
                    if len(parts) >= 3:
                        col_name = parts[0]
                        # Check pk
                        is_pk = parts[1].lower() in ('true', 'yes', '✅')
                        # Check fk
                        is_fk = parts[2].lower() in ('true', 'yes', '✅')
                        ref_table = None
                        ref_col = None
                        
                        if len(parts) >= 5:
                            ref_table = parts[3]
                            ref_col = parts[4]
                        
                        # Fix up if ref_table is specified but is_fk isn't true
                        if ref_table and ref_table.lower() != 'null':
                            is_fk = True
                            
                        columns.append(ColumnInfo(col_name, is_pk, is_fk, ref_table, ref_col))
            else:
                # Add to description
                description_lines.append(line_str)
                
        if table_name:
            description = " ".join(description_lines)
            tables.append(TableSchema(table_name, description, columns))
            
    return tables

def parse_json_schema(json_str):
    data = json.loads(json_str)
    tables = []
    
    # Check if format matches { tables: [...], foreign_keys: [...] }
    if isinstance(data, dict) and "tables" in data:
        tbl_list = data["tables"]
        fk_list = data.get("foreign_keys", [])
        
        # Build map of table_name -> TableSchema
        tbl_map = {}
        for item in tbl_list:
            name = item.get("name")
            desc = item.get("description", "")
            columns = []
            for col in item.get("columns", []):
                columns.append(ColumnInfo(
                    name=col.get("name"),
                    is_pk=col.get("is_pk", False),
                    is_fk=col.get("is_fk", False),
                    ref_table=col.get("ref_table"),
                    ref_col=col.get("ref_col")
                ))
            tbl_map[name] = TableSchema(name, desc, columns)
            
        # Parse global FK list if present
        for fk in fk_list:
            tbl_name = fk.get("table")
            col_name = fk.get("column")
            ref_tbl = fk.get("ref_table")
            ref_col = fk.get("ref_column")
            
            if tbl_name in tbl_map:
                # Find matching column
                found = False
                for col in tbl_map[tbl_name].columns:
                    if col.name == col_name:
                        col.is_fk = True
                        col.ref_table = ref_tbl
                        col.ref_col = ref_col
                        found = True
                        break
                if not found:
                    tbl_map[tbl_name].columns.append(ColumnInfo(col_name, is_pk=False, is_fk=True, ref_table=ref_tbl, ref_col=ref_col))
                    
        return list(tbl_map.values())
        
    # Alternate simple JSON list format: [ { name: ..., description: ..., columns: [...] } ]
    elif isinstance(data, list):
        for item in data:
            name = item.get("name")
            desc = item.get("description", "")
            columns = []
            for col in item.get("columns", []):
                columns.append(ColumnInfo(
                    name=col.get("name"),
                    is_pk=col.get("is_pk", False),
                    is_fk=col.get("is_fk", False),
                    ref_table=col.get("ref_table"),
                    ref_col=col.get("ref_col")
                ))
            tables.append(TableSchema(name, desc, columns))
        return tables
    else:
        raise ValueError("Invalid JSON schema format")

class SchemaRetriever:
    def __init__(self, tables, model_name='all-MiniLM-L6-v2'):
        self.tables = tables
        self.table_map = {t.name: t for t in tables}
        
        # Build FK graph
        self.graph = nx.Graph()
        for t in tables:
            self.graph.add_node(t.name)
            for col in t.columns:
                if col.is_fk and col.ref_table:
                    self.graph.add_edge(t.name, col.ref_table, weight=1.0)
                    
        # Load embedding model locally with TF-IDF fallback
        try:
            self.model = SentenceTransformer(model_name)
            self.use_fallback_tfidf = False
        except Exception as e:
            print(f"WARNING: Failed to load SentenceTransformer model '{model_name}'. Falling back to local TF-IDF vectorizer. Error: {e}")
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.model = TfidfVectorizer()
            self.use_fallback_tfidf = True
            
        # Preprocess documents
        self.docs = []
        self.table_names = []
        for t in tables:
            self.table_names.append(t.name)
            self.docs.append(self._create_table_doc(t))
            
        # BM25 setup
        tokenized_docs = [self._tokenize(doc) for doc in self.docs]
        self.bm25 = BM25Okapi(tokenized_docs)
        
        # Embed documents
        if not self.use_fallback_tfidf:
            self.doc_embeddings = self.model.encode(self.docs, convert_to_tensor=False)
            self.doc_embeddings = np.array(self.doc_embeddings)
        else:
            self.doc_embeddings = self.model.fit_transform(self.docs).toarray()
        
    def _stem(self, word):
        """Very small, conservative suffix stripper -- not a real Porter
        stemmer, just enough to collapse the common verb/noun-form
        mismatches (delivered/delivery-ish, purchased/purchase, viewed/
        viewing/views, returned/returns) that a pure token-match approach
        (BM25 / TF-IDF, no semantic model) is otherwise blind to. Applied
        identically to both table documents and queries so they stay
        comparable."""
        if len(word) <= 4:
            return word
        if word.endswith("ing") and len(word) > 6:
            return word[:-3]
        if word.endswith("ies") and len(word) > 5:
            return word[:-3] + "y"
        if word.endswith("ed") and len(word) > 5:
            return word[:-2]
        if word.endswith("es") and len(word) > 5:
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss") and len(word) > 4:
            return word[:-1]
        return word

    def _tokenize(self, text):
        stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "arent",
            "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "cant",
            "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt", "doing", "dont", "down", "during",
            "each", "few", "for", "from", "further", "had", "hadnt", "has", "hasnt", "have", "havent", "having",
            "he", "hed", "hell", "hes", "her", "here", "heres", "hers", "herself", "him", "himself", "his", "how",
            "hows", "i", "id", "ill", "im", "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets",
            "me", "more", "most", "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
            "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shant", "she",
            "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that", "thats", "the",
            "their", "theirs", "them", "themselves", "then", "there", "theres", "these", "they", "theyd", "theyll",
            "theyre", "theyve", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was",
            "wasnt", "we", "wed", "well", "were", "weve", "werent", "what", "whats", "when", "whens", "where",
            "wheres", "which", "while", "who", "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt",
            "you", "youd", "youll", "youre", "youve", "your", "yours", "yourself", "yourselves", "show", "find",
            "list", "get", "give", "display", "retrieve", "currently", "are", "have", "who", "been", "already", "but"
        }
        tokens = re.findall(r'\b[a-z_]+\b', text.lower())
        return [self._stem(t) for t in tokens if t not in stopwords]
        
    def _create_table_doc(self, table):
        # Expand name and columns
        expanded_name = expand_name(table.name)
        expanded_cols = []
        for col in table.columns:
            expanded_cols.append(col.name)
            if col.is_fk:
                # FK columns (e.g. payment_id on rfnd_log) are kept as their raw
                # compound name only, NOT word-expanded into "payment id".
                # Expanding them injects the *referenced* table's own core
                # vocabulary ("payment") as a standalone matchable term on this
                # table's document -- so any query about payments would also
                # lexically match rfnd_log purely because it references pay_trn
                # via FK, even with zero refund context. The FK relationship is
                # still fully available to the retriever through the graph
                # (built from col.is_fk / col.ref_table) -- that's the correct
                # channel for "this table is reachable from that one"; it
                # shouldn't also leak into lexical scoring.
                continue
            expanded_cols.append(expand_name(col.name))
        cols_str = " ".join(set(expanded_cols))
        
        # Refined clean synonyms
        synonyms = {
            "customer": "user customer customers registered client clients buyer buyers buyer's profile account accounts",
            "cust_addr": "address addresses shipping billing location locations home delivery zip postal city state",
            "seller_mst": "seller sellers vendor vendors merchant merchants shop shops store stores rating",
            "category": "category categories hierarchy classification classifications labels parent child",
            "product": "product products item items goods merchandise catalog brand brand name SKU sku stock out of stock out-of-stock",
            "inv_stock": "inventory stock qty quantity available reserve warehouse level stock_id out of stock out-of-stock",
            "warehouse": "warehouse warehouses storage store depot location city state inventory stock out of stock out-of-stock",
            "tbl_ord_hdr": "order orders ordered ordering checkout date status total amount bill coupon purchase purchased purchasing purchase purchased purchasing purchase purchased purchasing transaction header placed place",
            "tbl_ord_item": "order item order items products ordered ordering purchase purchased purchasing purchase purchased purchasing purchase purchased purchasing cart quantity price checkout details lines",
            "pay_trn": "payment transaction payments paid paying card cash check billing method record status txn ref",
            "ship_hdr": "shipment shipments shipping shipped delivery delivered deliver status carrier tracking number tracking_no ship date",
            "return_req": "return returns request requests returned returning exchange reason refund request_date status",
            "rfnd_log": "refund refunds refunded refunding payout payback log refund amount refund status",
            "coupon": "coupon coupons discount discounts promo code offer valid voucher vouchers reduction discount value",
            "review": "review reviews reviewed reviewing rating feedback text stars comment comments critique rating stars",
            "cart_item": "cart item cart items shopping cart basket bag added adding quantity pending checkout",
            "wishlist_item": "wishlist wishlists saved saving favorite favorites bookmark future purchase purchased wishlist id",
            "recently_viewed": "recently viewed views viewing browse browsing tracking log clicked page visit",
            "recommendation_log": "recommendation recommendations recommended products engine score matching suggested suggested product"
        }
        syns = synonyms.get(table.name.lower(), "")
        
        # Boost table name matching weight by repeating name and synonyms 5 times
        name_boost = " ".join([table.name, expanded_name] * 5)
        syns_boost = " ".join([syns] * 10)
        doc = f"Table Name: {name_boost}. Description: {table.description} {table.description} {syns_boost}. Columns: {cols_str}."
        return doc

    def search(self, query, top_k=5, alpha=0.45, seed_threshold=0.25, use_graph=True, graph_hops=3):
        # 1. BM25 score
        tokenized_query = self._tokenize(query)
        bm25_scores = np.array(self.bm25.get_scores(tokenized_query))
        
        # Direct primary terms match boost to counter IDF dilution
        primary_terms = {
            "customer": {"customer", "customers"},
            "cust_addr": {"address", "addresses", "addr"},
            "seller_mst": {"seller", "sellers", "vendor", "vendors"},
            "category": {"category", "categories"},
            "product": {"product", "products", "item", "items"},
            "inv_stock": {"stock", "inventory", "qty"},
            "warehouse": {"warehouse", "warehouses"},
            "tbl_ord_hdr": {"order", "orders", "purchased"},
            "tbl_ord_item": {"order", "orders", "item", "items"},
            "pay_trn": {"payment", "payments", "transaction", "transactions"},
            "ship_hdr": {"shipment", "shipments", "shipping", "delivery", "delivered"},
            "return_req": {"return", "returns", "returned"},
            "rfnd_log": {"refund", "refunds", "refunded"},
            "coupon": {"coupon", "coupons", "discount", "discounts"},
            "review": {"review", "reviews", "rating", "ratings"},
            "cart_item": {"cart", "basket", "shopping"},
            "wishlist_item": {"wishlist", "wishlists", "saved", "favorite", "favorites", "bookmark"},
            "recently_viewed": {"recently", "viewed", "views", "viewing", "browse", "browsed", "browsing"},
            "recommendation_log": {"recommendation", "recommendations", "recommended", "suggested", "suggest"}
        }
        # Min-max scale BM25 first to prevent scale distortion when boosting
        if len(bm25_scores) > 0 and (max(bm25_scores) - min(bm25_scores)) > 1e-9:
            bm25_scores = (bm25_scores - min(bm25_scores)) / (max(bm25_scores) - min(bm25_scores))
        else:
            bm25_scores = np.zeros_like(bm25_scores)
            
        # Direct primary terms match boost to scaled scores (capping at 1.0)
        for i, name in enumerate(self.table_names):
            if name in primary_terms:
                stemmed_terms = {self._stem(w) for w in primary_terms[name]}
                if any(w in tokenized_query for w in stemmed_terms):
                    bm25_scores[i] = min(1.0, bm25_scores[i] + 0.30)
            
        # 2. Dense score
        if not self.use_fallback_tfidf:
            query_emb = self.model.encode(query, convert_to_tensor=False)
            query_emb = np.array(query_emb)
            norm_query = np.linalg.norm(query_emb)
            norm_docs = np.linalg.norm(self.doc_embeddings, axis=1)
            dense_scores = np.dot(self.doc_embeddings, query_emb) / (norm_docs * norm_query + 1e-9)
        else:
            query_emb = self.model.transform([query]).toarray()[0]
            norm_query = np.linalg.norm(query_emb)
            norm_docs = np.linalg.norm(self.doc_embeddings, axis=1)
            dense_scores = np.dot(self.doc_embeddings, query_emb) / (norm_docs * norm_query + 1e-9)
        
        # Use raw cosine similarity, clipped to [0, 1]
        dense_scores = np.clip(dense_scores, 0, 1)
            
        # Combined score
        combined_scores = alpha * dense_scores + (1 - alpha) * bm25_scores
        table_scores = {self.table_names[i]: combined_scores[i] for i in range(len(self.table_names))}
        
        # Determine top raw matching score
        raw_top_score = max(table_scores.values())
        
        # Choose strong seeds dynamically based on score exceeding 40% of the top raw matching score
        strong_seed_threshold = 0.40 * raw_top_score
        strong_seeds = []
        
        # Log/interaction table unique defining keywords check
        log_tables = {"cart_item", "wishlist_item", "recently_viewed", "recommendation_log"}
        
        for name, score in table_scores.items():
            if score >= strong_seed_threshold:
                if name in log_tables:
                    # Only allow as seed if at least one unique keyword matches the query
                    terms = primary_terms.get(name, set())
                    if not any(kw in query.lower() for kw in terms):
                        continue
                strong_seeds.append(name)
                
        # Ensure we have at least the top-1 table as fallback seed
        if not strong_seeds:
            top_table = max(table_scores, key=table_scores.get)
            strong_seeds.append(top_table)
            
        # Bridges & Graph traversal
        graph = nx.Graph()
        log_tables = {"cart_item", "wishlist_item", "recently_viewed", "recommendation_log"}
        for t in self.tables:
            graph.add_node(t.name)
            for col in t.columns:
                if col.is_fk and col.ref_table:
                    # Prefer core transaction paths by setting higher weight for log/history tables
                    edge_wt = 1.0
                    if t.name in log_tables or col.ref_table in log_tables:
                        edge_wt = 3.0
                    graph.add_edge(t.name, col.ref_table, weight=edge_wt)
                    
        bridging_tables = set()
        bridging_floors = {}
        discount = 0.55
        
        # Bridging paths are found ONLY between strong_seeds
        if len(strong_seeds) >= 2:
            for i in range(len(strong_seeds)):
                for j in range(i + 1, len(strong_seeds)):
                    u = strong_seeds[i]
                    v = strong_seeds[j]
                    if graph.has_node(u) and graph.has_node(v):
                        try:
                            # Use Dijkstra's shortest path
                            path = nx.shortest_path(graph, source=u, target=v, weight='weight')
                            if len(path) <= graph_hops + 1:
                                # Bridging floor relative to the seeds it connects (weaker discounted)
                                floor = discount * min(table_scores[u], table_scores[v])
                                # Only add intermediate path nodes, not endpoints
                                for node in path[1:-1]:
                                    bridging_tables.add(node)
                                    bridging_floors[node] = max(bridging_floors.get(node, 0.0), floor)
                        except nx.NetworkXNoPath:
                            pass
                            
        # The candidate tables are seeds + bridges + 1-hop neighbors
        final_scores = {}
        
        # Initialize final scores ONLY for strong seeds to shield raw scores of non-seeds
        for name in strong_seeds:
            final_scores[name] = table_scores[name]
            
        # Boost bridging tables to make sure they are preserved and rank well
        for name in bridging_tables:
            if name in strong_seeds:
                final_scores[name] = max(final_scores[name], bridging_floors.get(name, 0.0))
            else:
                final_scores[name] = bridging_floors.get(name, 0.0)
            
        # Apply degree-normalized 1-hop neighbor boost (taking the max boost per neighbor, scaled by seed score)
        base_boost = 0.80
        neighbor_boosts = {}
        for u in strong_seeds:
            if graph.has_node(u):
                degree = graph.degree(u)
                if degree > 0:
                    boost = base_boost * table_scores[u] / degree
                    for v in graph.neighbors(u):
                        if table_scores.get(v, 0.0) > 0.05:
                            neighbor_boosts[v] = max(neighbor_boosts.get(v, 0.0), boost)
                            
        # Also propagate a discounted version of the same boost from bridging
        # tables (not just strong seeds) -- but ONLY from narrow (low-degree)
        # bridging tables, e.g. tbl_ord_item connecting to product. A bridging
        # table that is itself a hub (e.g. product, 9 neighbors) must NOT
        # propagate further -- doing so re-floods the same false positives the
        # nonzero-score gate was meant to stop, just via a different source.
        bridge_boost_discount = 0.55
        bridge_hub_degree_cap = 4
        for u in bridging_tables:
            if graph.has_node(u):
                degree = graph.degree(u)
                if degree > bridge_hub_degree_cap:
                    continue
                u_score = bridging_floors.get(u, table_scores.get(u, 0.0))
                if degree > 0 and u_score > 0:
                    boost = bridge_boost_discount * base_boost * u_score / degree
                    for v in graph.neighbors(u):
                        if v in strong_seeds or v in bridging_tables:
                            continue
                        if table_scores.get(v, 0.0) > 0.05:
                            neighbor_boosts[v] = max(neighbor_boosts.get(v, 0.0), boost)
                            
        for v, boost in neighbor_boosts.items():
            if v in strong_seeds or v in bridging_tables:
                final_scores[v] = max(final_scores[v], boost)
            else:
                # Bug fix: floor must be the candidate's own real base score
                # (table_scores[v]), not a bare 0.0 -- otherwise real signal
                # (e.g. product at 0.211) gets silently flattened down to a
                # smaller structural boost (e.g. 0.05).
                final_scores[v] = max(final_scores.get(v, table_scores.get(v, 0.0)), boost)

        # Universal keyword gate: for any table that entered final_scores via
        # neighbor-boost or bridge-boost (not as a strong seed itself),
        # ensure it has a real primary term match in the tokenized query.
        for name in list(final_scores.keys()):
            if name in strong_seeds:
                continue  # seeds already validated via strong_seed_threshold
            terms = primary_terms.get(name, set())
            stemmed_terms = {self._stem(w) for w in terms}
            if terms and not any(w in tokenized_query for w in stemmed_terms):
                del final_scores[name]

        # Sort candidate tables
        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Gap-based cutoff (elbow method)
        if ranked:
            if len(ranked) <= 3:
                return ranked
                
            max_rel_drop = -1.0
            cutoff_idx = 0
            
            # Find the largest relative drop between consecutive scores (elbow)
            # We start looking from index i = 2 to ensure we always keep at least 3 tables
            for i in range(2, len(ranked) - 1):
                s_curr = ranked[i][1]
                s_next = ranked[i+1][1]
                
                if s_curr >= 0.15:
                    rel_drop = (s_curr - s_next) / (s_curr + 1e-9)
                    if rel_drop > max_rel_drop:
                        max_rel_drop = rel_drop
                        cutoff_idx = i
            
            # Ensure we do not discard any candidate scoring >= 0.38 * raw_top_score
            min_keep_score = 0.38 * raw_top_score
            for idx, (name, score) in enumerate(ranked):
                if score >= min_keep_score:
                    cutoff_idx = max(cutoff_idx, idx)
            
            # If no sharp elbow (relative drop >= 0.18) was detected,
            # fall back to a relative floor tied to the raw top score
            if max_rel_drop < 0.18:
                cutoff_score = 0.40 * raw_top_score
                filtered_ranked = [item for item in ranked if item[1] >= cutoff_score]
                if not filtered_ranked:
                    filtered_ranked = [ranked[0]]
                return filtered_ranked
                
            return ranked[:cutoff_idx + 1]
        else:
            return []
