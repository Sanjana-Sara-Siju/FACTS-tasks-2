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

# IMPORTING PROMPT FROM SEPARATE FILE
from prompt import EXTRACTION_PROMPT, ITEM_MAPPING_PROMPT

# LOADING API KEY
load_dotenv() 
apiKey = os.getenv("MISTRAL_API_KEY")
mongoUri = os.getenv("MONGO_URI")
model = "mistral-large-latest"
client = Mistral(api_key = apiKey)

# SETTING UP FOLDER
backup_folder = "PDFs"
os.makedirs(backup_folder, exist_ok = True) # creates folder if it doesn't exist 

# INITIALIZING MONGODB CONNECTION
print("Connecting to MongoDB...")
mongo_client = MongoClient(mongoUri)
db = mongo_client["JSON_PDF_database"]    # The name of your new database
collection = db["extracted_pdfs"]        # The name of the collection (like a table)

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

    # security block
    blocked = ['delete', 'update', 'drop', 'grant', 'alter', 'create', 'insert', 'revoke', 'truncate', 'merge', 'exec']

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

        # INJECTING PDF TEXT INTO THE IMPORTED PROMPT
        prompt = EXTRACTION_PROMPT.format(pdf_text = pdf_text)

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

            # processing AI-generated party query
            party_query = extracted_data.get("party_sql_query", "")

            if party_query:
                is_safe = True

                # applying SQL security checks
                for word in blocked:
                    if word in party_query.lower():
                        print(f"Warning! Operation '{word}' not allowed. Blocking party query.")
                        is_safe = False
                        break
                if 'select *' in party_query.lower() or 'select*' in party_query.lower():
                    print("Warning! SELECT * operation not allowed. Blocking party query.")
                    is_safe = False

                if is_safe:
                    print(f"Executing party query: {party_query}")
                    sql_cursor.execute(party_query)
                    party_result = sql_cursor.fetchone()
                    
                    if party_result:
                        extracted_data["facts_party_code"] = party_result["PARTYMST_DOCNO"]
                        extracted_data["facts_party_desc"] = party_result["PARTYMST_DESC"]
                    else:
                        extracted_data["facts_party_code"] = "NOT FOUND"
                        extracted_data["facts_party_desc"] = "NOT FOUND"
                else:
                    extracted_data["facts_party_code"] = "BLOCKED FOR SECURITY"
            
            # FUZZY MATCHING (RAG) FOR ITEMS 
            party_code = extracted_data.get("facts_party_code")
            history_query = extracted_data.get("history_sql_query", "") 
            
            # only looking up history if its a valid client and the query exists
            if party_code not in ["NOT FOUND", "BLOCKED FOR SECURITY"] and history_query:
                print(f"Executing history query for client...")
                
                # security check on history query
                is_history_safe = True
                for word in blocked:
                    if word in history_query.lower():
                        is_history_safe = False
                        break
                
                if is_history_safe and 'select *' not in history_query.lower():
                    sql_cursor.execute(history_query)
                    history_results = sql_cursor.fetchall()
                    
                    # formatting the data for Mistral 
                    if history_results:
                        history_text = "\n".join([str(row) for row in history_results])
                    else:
                        history_text = "No previous purchase history found for this client..."

                    print(f"\n--- WHAT THE DATABASE FOUND IN HISTORY ---\n{history_text}\n-----------------------------------\n")

                    # PDF items mapping
                    items_list = extracted_data.get("items") or []
                    
                    for item in items_list:
                        raw_item_name = item.get("item_name", "")
                        
                        if raw_item_name:
                            print(f"Fuzzy matching mapping for: '{raw_item_name}'...")
                            
                            mapping_prompt = ITEM_MAPPING_PROMPT.format(
                                extracted_item = raw_item_name,
                                history_list = history_text
                            )
                            
                            mapping_response = client.chat.complete(
                                model = "mistral-small-latest",
                                messages = [
                                    {"role": "system", "content": "You strictly output JSON."},
                                    {"role": "user", "content": mapping_prompt}
                                ],
                                response_format = {"type": "json_object"}
                            )
                            
                            mapped_data = json.loads(mapping_response.choices[0].message.content)
                            item["facts_stock_code"] = mapped_data.get("facts_stock_code", "NOT FOUND")
                            item["facts_stock_desc"] = mapped_data.get("facts_stock_desc", "NOT FOUND")

                            # GLOBAL HISTORY FALLBACK 
                            # grabbing the query directly from specific item
                            fallback_query = item.get("fallback_sql_query", "")
                            
                            if item["facts_stock_code"] == "NOT FOUND" and fallback_query:
                                print(f"Not in client history (or client link broken). Executing AI specific fallback for: {raw_item_name}")
                                
                                # security check 
                                is_fallback_safe = True
                                for word in blocked:
                                    if word in fallback_query.lower():
                                        is_fallback_safe = False
                                        break
                                
                                if is_fallback_safe and 'select *' not in fallback_query.lower():
                                    sql_cursor.execute(fallback_query)
                                    fallback_result = sql_cursor.fetchone()
                                    
                                    if fallback_result:
                                        print("Match found in global purchase_details!")
                                        
                                        # trick to grab the first 2 columns regardless of their name
                                        result_values = list(fallback_result.values())
                                        if len(result_values) >= 2:
                                            item["facts_stock_code"] = str(result_values[0])
                                            item["facts_stock_desc"] = str(result_values[1])
                                    else:
                                        print("Item not found anywhere in historical details.")
                           

        except Exception as e:
            print(f"Database enrichment failed: {e}")
            extracted_data["sql_enrichment_error"] = str(e)
            
        finally:
            if sql_conn is not None:
                sql_conn.close()
                print("SQL connection closed.")

        # INSERTING DIRECTLY INTO MONGODB
        insert_result = collection.insert_one(extracted_data)
        results.append(file.filename) 

    print("\nAll PDFs processed and uploaded to MongoDB successfully!")
    return {"status": "success", "processed_files": results}

#  ROUTE --> HANDLING DOCUMENT SEARCHES
@app.get("/search")
async def search_database(query: str):
    print(f"Searching database for: {query}")

    # FLEXIBLE SEARCH ACROSS MULTIPLE FIELDS
    # $regex --> provides regular expression capabilities for pattern matching within string fields in queries
    search_filter = {
        "$or": [ # $or --> logical OR operation
            {"source_pdf_filename": {"$regex": query, "$options": "i"}},
            {"document_number": {"$regex": query, "$options": "i"}}, 
            {"external_party_name": {"$regex": query, "$options": "i"}},   
        ]
    }

    # "_id": 0 --> to hide the MongoDB ObjectID cuz FastAPI can't convert BSON to JSON natively
    results_cursor = collection.find(search_filter, {"_id": 0})
    
    # converting cursor to a list of dictionaries
    results_list = list(results_cursor)
    
    return {"count": len(results_list), "data": results_list}


#             # Processing AI-generated stock queries
#             items_list = extracted_data.get("items") or [] # to handle when there are no items
#             for item in items_list:
#                 stock_query = item.get("stock_sql_query", "")
                
#                 if stock_query:
#                     is_safe = True
                    
#                     # applying SQL security checks 
#                     for word in blocked:
#                         if word in stock_query.lower():
#                             print(f"Warning! Operation '{word}' not allowed. Blocking stock query.")
#                             is_safe = False
#                             break
#                     if 'select *' in stock_query.lower() or 'select*' in stock_query.lower():
#                         print("Warning! SELECT * operation not allowed. Blocking stock query.")
#                         is_safe = False

#                     if is_safe:
#                         print(f"Executing stock query: {stock_query}")
#                         sql_cursor.execute(stock_query)
#                         stock_result = sql_cursor.fetchone()
                        
#                         if stock_result:
#                             item["facts_stock_code"] = stock_result["STKMST_DOCNO"]
#                             item["facts_stock_desc"] = stock_result["STKMST_DESC"]
#                         else:
#                             item["facts_stock_code"] = "NOT FOUND"
#                             item["facts_stock_desc"] = "NOT FOUND"
#                     else:
#                         item["facts_stock_code"] = "BLOCKED FOR SECURITY"

#         except Exception as e:
#             print(f"Database enrichment failed: {e}")
#             extracted_data["sql_enrichment_error"] = str(e)
            
#         finally:
#             if sql_conn is not None:
#                 sql_conn.close()
#                 print("SQL connection closed.")

# # INSERTING DIRECTLY INTO MONGODB
#         insert_result = collection.insert_one(extracted_data)
#         results.append(file.filename) 

#     print("\nAll PDFs processed and uploaded to MongoDB successfully!")