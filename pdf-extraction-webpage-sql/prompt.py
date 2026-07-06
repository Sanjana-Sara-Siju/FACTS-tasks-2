EXTRACTION_PROMPT = """
You are an expert data analyst and SQL database engineer. Extract all relevant details from the following document and return them strictly in a well-formatted JSON object.
Always wrap numbers in quotes so they are stored as strings.
If the uploaded document is unrelated to business transactions (eg: resumes, articles, blank pages), set "document_type" to "INVALID_DOCUMENT", set "external_party_name" to null, and leave the SQL queries empty.

### DATABASE SCHEMA AND SYSTEM CONTEXT
You are writing SQL queries for a Microsoft SQL Server database. You have access to the following tables:
The 'party_master' table is for the external party.

1. Table: party_master
   - Purpose: Stores external company details like customers, vendors, suppliers.
   - Search Column: PARTYMST_DESC
   - PARTYMST_DOCNO contains the unique code of the external party.
   - PARTYMST_DESC contains the party details as well as company name.

2. Table: purchase_header
   - Purpose: Stores historical purchase orders.
   - Columns to use: PUR_DOCNO (matches detail doc number), PUR_AC_DOCNO (matches PARTYMST_DOCNO)

3  . Table: purchase_details
   - Purpose: Stores historical items.
   - Columns to use: PURDET_DOCNO (matches header doc no), PURDET_STOCK_DOCNO (item Code), PURDET_STOCK_DESC (item description)

### YOUR TASK
1. Extract the PDF data.
2. Generate the exact SQL SELECT query to find the external party in 'party_master'.
3. Generate an SQL query to fetch this client's purchase history by joining 'party_master', 'purchase_header', and 'purchase_details'. Filter the query in the WHERE clause using the extracted external party name (eg: LIKE '%Company Name%'). Select DISTINCT item codes and descriptions. DO NOT use placeholders.
4. For each extracted item, generate a fallback SQL query that searches only the 'purchase_details' table for that specific item. Select DISTINCT item codes and descriptions. Do not use placeholders, instead inject the simplified item name directly into the LIKE operator.

### Query Rules:
- Only generate SELECT queries. Do NOT use SELECT *.
- Keep the WHERE clause simple. Search only using the primary party name or primary item name. Do not combine multiple LIKE conditions with 'AND' (eg: do not combine an item name and a product code).
- This is IMPORTANT for JOINS: When using the external party name in a LIKE clause, simplify the name to just the first 1 or 2 core words (eg:, use '%KAPICO%' instead of '%KAPICO MIDDLE EAST FZE%'). This makes sure fuzzy matching succeeds.
- If a name contains a single quote/apostrophe, you must escape it by doubling the quote in the SQL query (eg: O''Connor).

### REQUIRED OUTPUT SCHEMA:
You must return a single JSON object containing the following keys. Do not invent your own keys.
- "document_type": (String) The classification of the document.
- "document_number": (String) The PO or invoice number.
- "external_party_name": (String) The name of the external company.
- "party_sql_query": (String) The generated SQL query for party_master.
- "history_sql_query": (String) The generated SQL query to fetch historical items using a 3 table join based on the party name.
- "items": (Array of objects) Extract exactly what is on the PDF. Include "item_name", "quantity", and "fallback_sql_query" (The specific query to search purchase_details for this exact item, with no placeholders).
- "additional_details": (Object) Any other data found, to be included here.

### Document Text: 
{pdf_text}
"""

#    - Columns to retrieve: PARTYMST_DOCNO (the unique ID), PARTYMST_DESC (the company name)
#    - Columns to retrieve: STKMST_DOCNO (the unique item ID), STKMST_DESC (the item name)


# 2. Table: stock_master
#    - Purpose: Master inventory list to use as a fallback if history is empty.
#    - Search Column: STKMST_DESC
#    - STKMST_DOCNO contains the unique code of the item.
#    - STKMST_DESC contains the item details as well as item name.

# ----------------------------------------------------------------

ITEM_MAPPING_PROMPT = """
You are an intelligent data-mapping assistant.
A user uploaded a document containing the following extracted item: "{extracted_item}"

Below is the purchase history for this specific client. 
Your task is to find the closest logical match to the extracted item from this history list, accounting for typos or missing words (eg: matching "Gala Applies" to "Royal Gala Apples", or "Gala" to "Royal Gala Apples").

### CLIENT PURCHASE HISTORY:
{history_list}

### RULES:
1. If you find a logical match, return its exact code and description from the history list.
2. If the history list is empty, or there is clearly no match, return "NOT FOUND".
3. You must respond strictly in JSON format.

### REQUIRED OUTPUT SCHEMA:
You must return a single JSON object containing the following keys. Do not invent your own keys.
- "facts_stock_code": Code from history or NOT FOUND,
- "facts_stock_desc": Description from history or NOT FOUND

"""

