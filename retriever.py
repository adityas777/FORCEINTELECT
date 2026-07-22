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
        return [t for t in tokens if t not in stopwords]
        
    def _create_table_doc(self, table):
        # Expand name and columns
        expanded_name = expand_name(table.name)
        expanded_cols = []
        for col in table.columns:
            expanded_cols.append(col.name)
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
            "ship_hdr": "shipment shipments shipping shipped delivery status carrier tracking number tracking_no ship date",
            "return_req": "return returns request requests returned returning exchange reason refund request_date status",
            "rfnd_log": "refund refunds refunded refunding payout payback log payment transaction refund amount status",
            "coupon": "coupon coupons discount discounts promo code offer valid voucher vouchers reduction discount value",
            "review": "review reviews reviewed reviewing rating feedback text customer customers stars comment comments critique rating stars",
            "cart_item": "cart item cart items shopping cart basket bag added adding quantity pending checkout",
            "wishlist_item": "wishlist wishlists saved saving favorite favorites bookmark future purchase purchased wishlist id",
            "recently_viewed": "recently viewed views viewing browse history tracking log clicked viewed history",
            "recommendation_log": "recommendation recommendations recommended products engine score matching suggested suggested product"
        }
        syns = synonyms.get(table.name.lower(), "")
        
        # Boost table name and description by repeating them
        doc = f"Table Name: {table.name} {expanded_name} {table.name} {expanded_name}. Description: {table.description} {table.description} {syns}. Columns: {cols_str}."
        return doc

    def search(self, query, top_k=5, alpha=0.45, seed_threshold=0.22, use_graph=True, graph_hops=3):
        # 1. BM25 score
        tokenized_query = self._tokenize(query)
        bm25_scores = np.array(self.bm25.get_scores(tokenized_query))
        
        # Min-max scale BM25
        if len(bm25_scores) > 0 and (max(bm25_scores) - min(bm25_scores)) > 1e-9:
            bm25_scores = (bm25_scores - min(bm25_scores)) / (max(bm25_scores) - min(bm25_scores))
        else:
            bm25_scores = np.zeros_like(bm25_scores)
            
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
        
        # Choose seeds dynamically based on score exceeding seed_threshold baseline (endpoints for bridging)
        all_seeds = []
        for name, score in table_scores.items():
            if score >= seed_threshold:
                all_seeds.append(name)
                
        # Only strong seeds spawn neighbor boosts
        strong_seed_threshold = 0.50 * raw_top_score
        strong_seeds = [name for name in all_seeds if table_scores[name] >= strong_seed_threshold]
        
        # Ensure we have at least the top-1 table as fallback seed
        if not strong_seeds:
            top_table = max(table_scores, key=table_scores.get)
            strong_seeds.append(top_table)
            if top_table not in all_seeds:
                all_seeds.append(top_table)
            
        # Bridges & Graph traversal
        graph = nx.Graph()
        for t in self.tables:
            graph.add_node(t.name)
            for col in t.columns:
                if col.is_fk and col.ref_table:
                    graph.add_edge(t.name, col.ref_table, weight=1.0)
                    
        bridging_tables = set()
        bridging_floors = {}
        discount = 0.90
        
        if len(all_seeds) >= 2:
            for i in range(len(all_seeds)):
                for j in range(i + 1, len(all_seeds)):
                    u = all_seeds[i]
                    v = all_seeds[j]
                    if graph.has_node(u) and graph.has_node(v):
                        try:
                            # Use Dijkstra's shortest path
                            path = nx.shortest_path(graph, source=u, target=v, weight='weight')
                            if len(path) <= graph_hops + 1:
                                # Bridging floor relative to the seeds it connects
                                floor = discount * (table_scores[u] + table_scores[v]) / 2
                                for node in path:
                                    bridging_tables.add(node)
                                    bridging_floors[node] = max(bridging_floors.get(node, 0.0), floor)
                        except nx.NetworkXNoPath:
                            pass
                            
        # The candidate tables are seeds + bridges + 1-hop neighbors
        final_scores = {}
        candidate_tables = set(all_seeds).union(bridging_tables)
        
        # Initialize final scores with original table scores
        for name in candidate_tables:
            final_scores[name] = table_scores[name]
            
        # Apply degree-normalized 1-hop neighbor boost (taking the max boost per neighbor, scaled by seed score)
        base_boost = 0.80
        neighbor_boosts = {}
        for u in strong_seeds:
            if graph.has_node(u):
                degree = graph.degree(u)
                if degree > 0:
                    boost = base_boost * table_scores[u] / degree
                    for v in graph.neighbors(u):
                        neighbor_boosts[v] = max(neighbor_boosts.get(v, 0.0), boost)
                            
        for v, boost in neighbor_boosts.items():
            candidate_tables.add(v)
            final_scores[v] = max(final_scores.get(v, table_scores[v]), boost)
                            
        # Boost bridging tables to make sure they are preserved and rank well
        for name in bridging_tables:
            final_scores[name] = max(final_scores.get(name, table_scores[name]), bridging_floors.get(name, 0.0))
                
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
            
            # If no sharp elbow (relative drop >= 0.18) was detected, keep all tables >= 0.20
            if max_rel_drop < 0.18:
                filtered_ranked = [item for item in ranked if item[1] >= 0.20]
                if not filtered_ranked:
                    filtered_ranked = [ranked[0]]
                return filtered_ranked
                
            return ranked[:cutoff_idx + 1]
        else:
            return []
