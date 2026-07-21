# customer

Stores registered customers and their account information.

| Column      | is_pk | is_fk | ref_table | ref_col |
| ----------- | ----- | ----- | --------- | ------- |
| customer_id | true  | false | null      | null    |
| cust_code   | false | false | null      | null    |
| full_name   | false | false | null      | null    |
| email       | false | false | null      | null    |
| phone       | false | false | null      | null    |
| status      | false | false | null      | null    |
| created_at  | false | false | null      | null    |

---

# cust_addr

Stores customer shipping and billing addresses.

| Column      | is_pk | is_fk | ref_table | ref_col     |
| ----------- | ----- | ----- | --------- | ----------- |
| addr_id     | true  | false | null      | null        |
| customer_id | false | true  | customer  | customer_id |
| addr_type   | false | false | null      | null        |
| line1       | false | false | null      | null        |
| city        | false | false | null      | null        |
| state       | false | false | null      | null        |
| postal_cd   | false | false | null      | null        |
| is_default  | false | false | null      | null        |

---

# seller_mst

Stores marketplace sellers.

| Column    | is_pk | is_fk | ref_table | ref_col |
| --------- | ----- | ----- | --------- | ------- |
| seller_id | true  | false | null      | null    |
| seller_nm | false | false | null      | null    |
| email     | false | false | null      | null    |
| rating    | false | false | null      | null    |
| is_active | false | false | null      | null    |

---

# category

Product categories.

| Column             | is_pk | is_fk | ref_table | ref_col     |
| ------------------ | ----- | ----- | --------- | ----------- |
| category_id        | true  | false | null      | null        |
| category_name      | false | false | null      | null        |
| parent_category_id | false | true  | category  | category_id |

---

# product

Master list of products sold on the platform.

| Column       | is_pk | is_fk | ref_table  | ref_col     |
| ------------ | ----- | ----- | ---------- | ----------- |
| product_id   | true  | false | null       | null        |
| category_id  | false | true  | category   | category_id |
| seller_id    | false | true  | seller_mst | seller_id   |
| sku          | false | false | null       | null        |
| product_name | false | false | null       | null        |
| brand        | false | false | null       | null        |
| is_active    | false | false | null       | null        |

---

# inv_stock

Current inventory available in warehouses.

| Column        | is_pk | is_fk | ref_table | ref_col      |
| ------------- | ----- | ----- | --------- | ------------ |
| stock_id      | true  | false | null      | null         |
| product_id    | false | true  | product   | product_id   |
| warehouse_id  | false | true  | warehouse | warehouse_id |
| qty_available | false | false | null      | null         |
| reserved_qty  | false | false | null      | null         |
| last_upd      | false | false | null      | null         |

---

# warehouse

Warehouses storing inventory.

| Column         | is_pk | is_fk | ref_table | ref_col |
| -------------- | ----- | ----- | --------- | ------- |
| warehouse_id   | true  | false | null      | null    |
| warehouse_name | false | false | null      | null    |
| city           | false | false | null      | null    |
| state          | false | false | null      | null    |

---

# tbl_ord_hdr

Customer order header.

| Column       | is_pk | is_fk | ref_table | ref_col     |
| ------------ | ----- | ----- | --------- | ----------- |
| ord_id       | true  | false | null      | null        |
| customer_id  | false | true  | customer  | customer_id |
| order_date   | false | false | null      | null        |
| sts_cd       | false | false | null      | null        |
| coupon_id    | false | true  | coupon    | coupon_id   |
| ship_addr_id | false | true  | cust_addr | addr_id     |
| total_amount | false | false | null      | null        |

---

# tbl_ord_item

Products belonging to an order.

| Column       | is_pk | is_fk | ref_table   | ref_col    |
| ------------ | ----- | ----- | ----------- | ---------- |
| ord_item_id  | true  | false | null        | null       |
| ord_id       | false | true  | tbl_ord_hdr | ord_id     |
| product_id   | false | true  | product     | product_id |
| qty          | false | false | null        | null       |
| unit_price   | false | false | null        | null       |
| discount_amt | false | false | null        | null       |

---

# pay_trn

Payment transactions for customer orders.

| Column         | is_pk | is_fk | ref_table   | ref_col |
| -------------- | ----- | ----- | ----------- | ------- |
| payment_id     | true  | false | null        | null    |
| ord_id         | false | true  | tbl_ord_hdr | ord_id  |
| payment_method | false | false | null        | null    |
| payment_status | false | false | null        | null    |
| txn_ref        | false | false | null        | null    |
| paid_amt       | false | false | null        | null    |
| paid_on        | false | false | null        | null    |

---

# ship_hdr

Shipment details.

| Column          | is_pk | is_fk | ref_table   | ref_col      |
| --------------- | ----- | ----- | ----------- | ------------ |
| shipment_id     | true  | false | null        | null         |
| ord_id          | false | true  | tbl_ord_hdr | ord_id       |
| warehouse_id    | false | true  | warehouse   | warehouse_id |
| carrier         | false | false | null        | null         |
| tracking_no     | false | false | null        | null         |
| shipped_date    | false | false | null        | null         |
| delivery_status | false | false | null        | null         |

---

# return_req

Customer return requests.

| Column        | is_pk | is_fk | ref_table    | ref_col     |
| ------------- | ----- | ----- | ------------ | ----------- |
| return_id     | true  | false | null         | null        |
| ord_item_id   | false | true  | tbl_ord_item | ord_item_id |
| reason        | false | false | null         | null        |
| request_date  | false | false | null         | null        |
| return_status | false | false | null         | null        |

---

# rfnd_log

Refund processing records.

| Column        | is_pk | is_fk | ref_table  | ref_col    |
| ------------- | ----- | ----- | ---------- | ---------- |
| refund_id     | true  | false | null       | null       |
| return_id     | false | true  | return_req | return_id  |
| payment_id    | false | true  | pay_trn    | payment_id |
| refund_amt    | false | false | null       | null       |
| refund_status | false | false | null       | null       |
| processed_on  | false | false | null       | null       |

---

# coupon

Coupons available to customers.

| Column         | is_pk | is_fk | ref_table | ref_col |
| -------------- | ----- | ----- | --------- | ------- |
| coupon_id      | true  | false | null      | null    |
| coupon_code    | false | false | null      | null    |
| discount_type  | false | false | null      | null    |
| discount_value | false | false | null      | null    |
| valid_from     | false | false | null      | null    |
| valid_to       | false | false | null      | null    |

---

# review

Customer product reviews.

| Column      | is_pk | is_fk | ref_table | ref_col     |
| ----------- | ----- | ----- | --------- | ----------- |
| review_id   | true  | false | null      | null        |
| product_id  | false | true  | product   | product_id  |
| customer_id | false | true  | customer  | customer_id |
| rating      | false | false | null      | null        |
| review_text | false | false | null      | null        |
| reviewed_on | false | false | null      | null        |

---

# cart_item

Stores products currently added to a customer's shopping cart but not yet purchased.

| Column       | is_pk | is_fk | ref_table | ref_col     |
| ------------ | ----- | ----- | --------- | ----------- |
| cart_item_id | true  | false | null      | null        |
| customer_id  | false | true  | customer  | customer_id |
| product_id   | false | true  | product   | product_id  |
| qty          | false | false | null      | null        |
| added_at     | false | false | null      | null        |

---

# wishlist_item

Products customers have saved for future purchase.

| Column      | is_pk | is_fk | ref_table | ref_col     |
| ----------- | ----- | ----- | --------- | ----------- |
| wishlist_id | true  | false | null      | null        |
| customer_id | false | true  | customer  | customer_id |
| product_id  | false | true  | product   | product_id  |
| created_at  | false | false | null      | null        |

---

# recently_viewed

Tracks products viewed by customers.

| Column      | is_pk | is_fk | ref_table | ref_col     |
| ----------- | ----- | ----- | --------- | ----------- |
| view_id     | true  | false | null      | null        |
| customer_id | false | true  | customer  | customer_id |
| product_id  | false | true  | product   | product_id  |
| viewed_at   | false | false | null      | null        |

---

# recommendation_log

Stores products recommended by the recommendation engine.

| Column       | is_pk | is_fk | ref_table | ref_col     |
| ------------ | ----- | ----- | --------- | ----------- |
| rec_id       | true  | false | null      | null        |
| customer_id  | false | true  | customer  | customer_id |
| product_id   | false | true  | product   | product_id  |
| algo_name    | false | false | null      | null        |
| score        | false | false | null      | null        |
| generated_at | false | false | null      | null        |