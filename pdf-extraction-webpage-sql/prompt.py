EXTRACTION_PROMPT = """
You are an expert data analyst and SQL database engineer. Extract all relevant details from the following document and return them strictly in a well-formatted JSON object.
Always wrap numbers in quotes so they are stored as strings.
If the uploaded document is unrelated to business transactions (eg: resumes, articles, blank pages), set "document_type" to "INVALID_DOCUMENT", set "external_party_name" to null, and leave the SQL queries empty.

### DATABASE SCHEMA AND SYSTEM CONTEXT
You are writing SQL queries for a Microsoft SQL Server database. You have access to the following tables:
The 'party_master' table is for the external party, and the 'stock_master' is for the items.

1. Table: party_master
   - Purpose: Stores external company details like customers, vendors, suppliers.
   - Search Column: PARTYMST_DESC
   - PARTYMST_DOCNO contains the unique code of the external party.
   - PARTYMST_DESC contains the party details as well as company name.

2. Table: stock_master
   - Purpose: Stores inventory and product item details.
   - Search Column: STKMST_DESC
   - STKMST_DOCNO contains the unique code of the item.
   - STKMST_DESC contains the item details as well as item name.


### YOUR TASK
1. Extract the PDF data.
2. Based on the schema above, generate the exact SQL SELECT queries required to find the internal ID codes for the extracted external party and the extracted items.

### Query Rules:
- Only generate SELECT queries.
- Do NOT use SELECT *. Explicitly name the columns you are retrieving.
- Use the LIKE operator with wildcards (eg:'%Name%') for flexible matching.
- Keep the WHERE clause simple. Search only using the primary party name or primary item name. Do not combine multiple LIKE conditions with 'AND' (eg: do not combine an item name and a product code).
- If a name contains a single quote/apostrophe, you must escape it by doubling the quote in the SQL query (eg: O''Connor).

### REQUIRED OUTPUT SCHEMA:
You must return a single JSON object containing the following keys. Do not invent your own keys.
- "document_type": (String) The classification of the document.
- "document_number": (String) The PO or invoice number.
- "external_party_name": (String) The name of the external company.
- "party_sql_query": (String) The generated SQL query for party_master.
- "items": (Array of Objects) Must contain "item_name", "quantity", and "stock_sql_query".
- "additional_details": (Object) Any other data found, to be included here.

### Document Text: 
{pdf_text}
"""

#    - Columns to retrieve: PARTYMST_DOCNO (the unique ID), PARTYMST_DESC (the company name)
#    - Columns to retrieve: STKMST_DOCNO (the unique item ID), STKMST_DESC (the item name)
