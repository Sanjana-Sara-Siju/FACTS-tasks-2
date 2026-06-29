import json
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from mistralai.client import Mistral
from pymongo import MongoClient
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse 
import io # to handle the byte streams
          # it lets Python treat raw memory like a physical file
import pymssql


# LOADING API KEY
load_dotenv() 
apiKey = os.getenv("MISTRAL_API_KEY")
mongoUri = os.getenv("MONGO_URI")
model = "mistral-small-latest"
client = Mistral(api_key = apiKey)

# SETTING UP FOLDER
backup_folder = "PDFs"
os.makedirs(backup_folder, exist_ok = True) # creates folder if it doesn't exist 

# INITIALIZING MONGODB CONNECTION
print("Connecting to MongoDB...")
mongo_client = MongoClient(mongoUri)
db = mongo_client["JSON_PDF_database"]    # The name of your new database
collection = db["sales_invoices"]        # The name of the collection (like a table)

# INITIALIZING WEB SERVER
app = FastAPI()

# ROUTE --> SERVING HTML PAGE
@app.get("/", response_class = HTMLResponse)
async def serve_frontend():
    with open("index.html", "r") as f:
        return f.read()
    
# ROUTE --> HANDLING FORM SUBMISSION
@app.post("/extract")
async def extract_data(files: list[UploadFile] = File(...)):
    results = []

    # loop through the uploaded files 
    for file in files:
        print(f"\n--- Processing {file.filename} ---")

        # reading raw bytes into memory 
        pdf_bytes = await file.read()

        # saving backup to hard drive
        backup_path = os.path.join(backup_folder, file.filename)
        with open(backup_path, "wb") as backup_file:
            backup_file.write(pdf_bytes)
    

    # EXTRACTING TEXT FROM PDF
    # wrapping the bytes in io.BytesIO so PdfReader treats it like an open file 
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pdf_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pdf_text += extracted + "\n"


        prompt = f"""
You are an expert data analyst. Extract all relevant details from the following document and return them strictly in a well-formatted JSON object. 
If a field is empty, return null for that field. Always wrap numbers in quotes so they are stored as strings.

Document Text: 
{pdf_text}

- The 'customer_name' will be used to search our 'party_master' database table.
- The 'item_name' inside the 'items' list will be used to search our 'stock_master' database table.
Extract these names exactly as they appear in the document so they can be matched accurately.

You MUST use the exact keys provided in the template below. Do not create nested objects for the customer or seller. If a field is not found in the document, return null for that field.
### EXPECTED JSON FORMAT:
{{
    "invoice_number": "value here or null",
    "order_number": "value here or null",
    "customer_name": "name of the buyer or company that is purchasing",
    "seller_name": "value here or null",
    "total_amount": "value here or null",
    "source_pdf_filename": "value here or null",
    "items": [
        {{
            "item_name": "name of the stock or product here",
            "quantity": "value here or null",
            "unit_price": "value here or null"
        }}
    ],
    "additional_details": {{
        // You may put any extra extracted data here
    }}
}}

"""


# CALLING MISTRAL API 
        print("Sending text to Mistral AI for extraction...")
        response = client.chat.complete(
        model = model, 
        messages = [
            {"role": "system", "content": "You are an assistant that strictly outputs JSON."},
            {"role": "user", "content": prompt}
        ],
        response_format = {"type": "json_object"} # forces the model to return valid JSON
    )

        # PRINTING TOKEN USAGE 
        prompt_tokens = response.usage.prompt_tokens
        completion_tokens = response.usage.completion_tokens
        total_tokens = response.usage.total_tokens
        print(f"Tokens Used --> Prompt: {prompt_tokens} | Output: {completion_tokens} | Total: {total_tokens}")

# CONVERTING RESPONSE STRING BACK INTO PYTHON 
        extracted_data = json.loads(response.choices[0].message.content)

# addition: adding filename as a new key-value pair to the dict Mistral created
        extracted_data["source_pdf_filename"] = file.filename

        # linear SQL Database Enrichment 
        party_name_from_pdf = extracted_data.get("customer_name", "") 
        
    
        try:
            # opening 1 connection for entire document
            sql_conn = pymssql.connect(
                server = os.getenv("SQL_SERVER"),
                port = os.getenv("SQL_PORT"),
                database = os.getenv("SQL_DATABASE"),
                user = os.getenv("SQL_USER"),
                password = os.getenv("SQL_PASSWORD"),
                login_timeout = 5
            )
            sql_cursor = sql_conn.cursor(as_dict = True)
            
            # fetching party (customer/vendor) data
            if party_name_from_pdf:
                print(f"Searching party_master for: {party_name_from_pdf}")
                party_query = "SELECT PARTYMST_DOCNO, PARTYMST_DESC FROM party_master WHERE PARTYMST_DESC LIKE %s"
                sql_cursor.execute(party_query, (f"%{party_name_from_pdf}%",))
                party_result = sql_cursor.fetchone()
                
                if party_result:
                    extracted_data["facts_party_code"] = party_result["PARTYMST_DOCNO"]
                    extracted_data["facts_party_desc"] = party_result["PARTYMST_DESC"]
                else:
                    extracted_data["facts_party_code"] = "NOT FOUND"
                    extracted_data["facts_party_desc"] = "NOT FOUND"

            # looping and fetching stock data for each item Mistral found
            items_list = extracted_data.get("items", [])
            for item in items_list:
                item_name = item.get("item_name", "")
                
                if item_name:
                    print(f"Searching stock_master for: {item_name}")
                    stock_query = "SELECT STKMST_DOCNO, STKMST_DESC FROM stock_master WHERE STKMST_DESC LIKE %s"
                    sql_cursor.execute(stock_query, (f"%{item_name}%",))
                    stock_result = sql_cursor.fetchone()
                    
                    if stock_result:
                        item["facts_stock_code"] = stock_result["STKMST_DOCNO"]
                        item["facts_stock_desc"] = stock_result["STKMST_DESC"]
                    else:
                        item["facts_stock_code"] = "NOT FOUND"
                        item["facts_stock_desc"] = "NOT FOUND"

        except Exception as e:
            print(f"Database enrichment failed: {e}")
            extracted_data["sql_enrichment_error"] = str(e)
            
        finally:
            if 'sql_conn' in locals():
                sql_conn.close()
                print("SQL Connection closed.")


# INSERTING DIRECTLY INTO MONGODB
        insert_result = collection.insert_one(extracted_data)
        results.append(file.filename) 


    print("\nAll PDFs processed and uploaded to MongoDB successfully!")

#  ROUTE --> HANDLING DOCUMENT SEARCHES
@app.get("/search")
async def search_database(query: str):
    print(f"Searching database for: {query}")

    # FLEXIBLE SEARCH ACROSS MULTIPLE FIELDS
    # $regex --> provides regular expression capabilities for pattern matching within string fields in queries
    search_filter = {
        "$or": [ # $or --> logical OR operation
            {"source_pdf_filename": {"$regex": query, "$options": "i"}},
            {"invoice_number": {"$regex": query, "$options": "i"}}, 
            {"order_number": {"$regex": query, "$options": "i"}}, 
            {"customer_name": {"$regex": query, "$options": "i"}},   
        ]
    }

    # "_id": 0 --> to hide the MongoDB ObjectID cuz FastAPI can't convert BSON to JSON natively
    results_cursor = collection.find(search_filter, {"_id": 0})
    
    # converting cursor to a list of dictionaries
    results_list = list(results_cursor)
    
    return {"count": len(results_list), "data": results_list}

