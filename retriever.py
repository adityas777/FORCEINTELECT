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
        
        # Build FK graph with semantic weights
        self.graph = nx.Graph()
        for t in tables:
            self.graph.add_node(t.name)
            for col in t.columns:
                if col.is_fk and col.ref_table:
                    edge_weight = 1.0
                    review_tables = {"review"}
                    peripheral_tables = {"cart_item", "wishlist_item", "recently_viewed", "recommendation_log"}
                    
                    if t.name in peripheral_tables or col.ref_table in peripheral_tables:
                        edge_weight = 4.0
                    elif t.name in review_tables or col.ref_table in review_tables:
                        edge_weight = 2.0
                        
                    if self.graph.has_edge(t.name, col.ref_table):
                        existing_weight = self.graph[t.name][col.ref_table].get('weight', 1.0)
                        edge_weight = min(edge_weight, existing_weight)
                        
                    self.graph.add_edge(t.name, col.ref_table, weight=edge_weight)
                    
        # Load embedding model locally
        self.model = SentenceTransformer(model_name)
        
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
        self.doc_embeddings = self.model.encode(self.docs, convert_to_tensor=False)
        self.doc_embeddings = np.array(self.doc_embeddings)
        
    def _tokenize(self, text):
        return re.findall(r'\w+', text.lower())
        
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
            "customer": "user customer registered client buyers profile account accounts",
            "cust_addr": "address addresses shipping billing location home delivery zip postal city state",
            "seller_mst": "seller sellers vendor vendors merchant merchants shop store rating",
            "category": "category categories hierarchy classification classifications labels parent child",
            "product": "product products item items goods merchandise catalog brand brand name SKU sku",
            "inv_stock": "inventory stock qty quantity available reserve warehouse level stock_id",
            "warehouse": "warehouse warehouses storage store depot location city state inventory stock",
            "tbl_ord_hdr": "order orders checkout date status total amount bill coupon purchase transaction header",
            "tbl_ord_item": "order item order items products ordered purchase cart quantity price checkout details lines",
            "pay_trn": "payment transaction payments paid card cash check billing method record status txn ref",
            "ship_hdr": "shipment shipments shipping delivery status carrier tracking number tracking_no ship date",
            "return_req": "return returns request returned exchange reason refund request_date status",
            "rfnd_log": "refund refunds payout payback log payment transaction refund amount status",
            "coupon": "coupon coupons discount promo code offer valid voucher reduction discount value",
            "review": "review reviews rating feedback text customer stars comment comments critique rating stars",
            "cart_item": "cart item cart items shopping cart basket bag added quantity pending checkout",
            "wishlist_item": "wishlist wishlists saved favorite favorites bookmark future purchase wishlist id",
            "recently_viewed": "recently viewed browse history tracking log clicked viewed history",
            "recommendation_log": "recommendation recommendations recommended products engine score matching suggested suggested product"
        }
        syns = synonyms.get(table.name.lower(), "")
        
        # Boost table name and description by repeating them
        doc = f"Table Name: {table.name} {expanded_name} {table.name} {expanded_name}. Description: {table.description} {table.description} {syns}. Columns: {cols_str}."
        return doc

    def search(self, query, top_k=5, alpha=0.55, seed_threshold=0.22, use_graph=True, graph_hops=3):
        # 1. BM25 score
        tokenized_query = self._tokenize(query)
        bm25_scores = np.array(self.bm25.get_scores(tokenized_query))
        
        # Min-max scale BM25
        if len(bm25_scores) > 0 and (max(bm25_scores) - min(bm25_scores)) > 1e-9:
            bm25_scores = (bm25_scores - min(bm25_scores)) / (max(bm25_scores) - min(bm25_scores))
        else:
            bm25_scores = np.zeros_like(bm25_scores)
            
        # 2. Dense score
        query_emb = self.model.encode(query, convert_to_tensor=False)
        query_emb = np.array(query_emb)
        norm_query = np.linalg.norm(query_emb)
        norm_docs = np.linalg.norm(self.doc_embeddings, axis=1)
        dense_scores = np.dot(self.doc_embeddings, query_emb) / (norm_docs * norm_query + 1e-9)
        
        # Min-max scale Dense
        if len(dense_scores) > 0 and (max(dense_scores) - min(dense_scores)) > 1e-9:
            dense_scores = (dense_scores - min(dense_scores)) / (max(dense_scores) - min(dense_scores))
        else:
            dense_scores = np.zeros_like(dense_scores)
            
        # Combined score
        combined_scores = alpha * dense_scores + (1 - alpha) * bm25_scores
        table_scores = {self.table_names[i]: combined_scores[i] for i in range(len(self.table_names))}
        
        # Apply heuristic filtering for seeds
        query_lower = query.lower()
        
        def check_heuristics(table_name, q_lower):
            indicators = {
                "customer": [r"\bcustomer", r"\buser", r"\bclient", r"\bbuyer", r"\bprofile", r"\baccount", r"\bregister"],
                "product": [r"\bproduct", r"\bitem", r"\bgoods", r"\bmerchandise", r"\bsku", r"\bbrand", r"\bsell"],
                "category": [r"\bcategory", r"\bcategories", r"\bclassif", r"\bgroup", r"\bparent", r"\bchild"],
                "inv_stock": [r"\bstock", r"\binventory", r"\bqty", r"\bquantity", r"\bwarehouse", r"\bdepot"],
                "cart_item": [r"\bcart", r"\bbasket", r"\bbag", r"\badd"],
                "wishlist_item": [r"\bwishlist", r"\bsave", r"\bbookmark", r"\bfavorite"],
                "recently_viewed": [r"\bviewed", r"\bbrowse", r"\bhistory", r"\bclick", r"\bvisit", r"\bview\b"],
                "recommendation_log": [r"\brecommend", r"\bsuggest", r"\balgo"],
                "rfnd_log": [r"\brefund", r"\bpayback", r"\blog", r"\brepay"],
                "return_req": [r"\breturn", r"\bexchange", r"\brefund", r"\bpayback"],
                "review": [r"\breview", r"\brating", r"\bstar", r"\bfeedback", r"\bcomment", r"\bcritique"],
                "coupon": [r"\bcoupon", r"\bdiscount", r"\bpromo", r"\bvoucher", r"\bcheckout"],
                "ship_hdr": [r"\bship", r"\bdelivery", r"\bcarrier", r"\btrack", r"\bdeliver"],
                "pay_trn": [r"\bpayment", r"\bpaid", r"\btxn", r"\btransaction", r"\bpay\b", r"\bcheckout"],
                "seller_mst": [r"\bseller", r"\bmerchant", r"\bvendor", r"\brating"],
                "cust_addr": [r"\baddress", r"\bshipping", r"\bbilling", r"\bcity", r"\bstate", r"\bpostal", r"\baddr"],
                "warehouse": [r"\bwarehouse", r"\bstock", r"\binventory", r"\bdepot", r"\bfulfillment", r"\bshipment"],
                "tbl_ord_hdr": [r"\border", r"\bpurchase", r"\bcheckout", r"\bbought", r"\bplaced"],
                "tbl_ord_item": [r"\bitem", r"\border\s+item", r"\bqty", r"\bquantity", r"\bprice", r"\bdiscount", r"\border\b", r"\bpurchase"]
            }
            name_lower = table_name.lower()
            if name_lower in indicators:
                return any(re.search(pattern, q_lower) is not None for pattern in indicators[name_lower])
            return True

        # Filter all table scores by heuristics first to eliminate irrelevant candidates
        valid_table_scores = {}
        for name, score in table_scores.items():
            if check_heuristics(name, query_lower):
                valid_table_scores[name] = score
                
        if not valid_table_scores:
            valid_table_scores = table_scores
            
        # Choose seeds dynamically based on score from valid candidates
        seeds = []
        for name, score in valid_table_scores.items():
            if score >= seed_threshold:
                seeds.append(name)
                
        # Ensure we have at least the top-1 table from the valid set
        top_table = max(valid_table_scores, key=valid_table_scores.get)
        if top_table not in seeds:
            seeds.append(top_table)
            
        # Bridges
        bridging_tables = set()
        if use_graph and len(seeds) >= 2:
            # Build query-specific graph dynamically
            graph = nx.Graph()
            for t in self.tables:
                graph.add_node(t.name)
                for col in t.columns:
                    if col.is_fk and col.ref_table:
                        edge_weight = 1.0
                        review_tables = {"review"}
                        peripheral_tables = {"cart_item", "wishlist_item", "recently_viewed", "recommendation_log"}
                        
                        if t.name in peripheral_tables or col.ref_table in peripheral_tables:
                            edge_weight = 4.0
                        elif t.name in review_tables or col.ref_table in review_tables:
                            edge_weight = 2.0
                            
                        # Adjust weights dynamically based on query
                        if t.name in peripheral_tables or t.name in review_tables:
                            if check_heuristics(t.name, query_lower):
                                edge_weight = 1.0
                                
                        ref_tbl = col.ref_table
                        if ref_tbl in peripheral_tables or ref_tbl in review_tables:
                            if check_heuristics(ref_tbl, query_lower):
                                edge_weight = 1.0
                                
                        if graph.has_edge(t.name, ref_tbl):
                            existing_weight = graph[t.name][ref_tbl].get('weight', 1.0)
                            edge_weight = min(edge_weight, existing_weight)
                            
                        graph.add_edge(t.name, ref_tbl, weight=edge_weight)
                        
            for i in range(len(seeds)):
                for j in range(i + 1, len(seeds)):
                    u = seeds[i]
                    v = seeds[j]
                    if graph.has_node(u) and graph.has_node(v):
                        try:
                            # Use Dijkstra's shortest path with dynamic query weights
                            path = nx.shortest_path(graph, source=u, target=v, weight='weight')
                            if len(path) <= graph_hops + 1:
                                for node in path:
                                    bridging_tables.add(node)
                        except nx.NetworkXNoPath:
                            pass
                            
        # The candidate tables are seeds + bridges
        candidate_tables = set(seeds).union(bridging_tables)
        
        # Rank candidate tables
        final_scores = {}
        for name in candidate_tables:
            score = table_scores[name]
            if name in bridging_tables and name not in seeds:
                score = max(score, 0.45)
            final_scores[name] = score
            
        # Sort candidate tables
        ranked = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return ranked
