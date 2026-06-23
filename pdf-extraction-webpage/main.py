import json
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from mistralai.client import Mistral
from pymongo import MongoClient
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse 


# LOADING API KEY
load_dotenv() 
apiKey = os.getenv("MISTRAL_API_KEY")
mongoUri = os.getenv("MONGO_URI")
model = "mistral-small-latest"
client = Mistral(api_key = apiKey)

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


    # EXTRACTING TEXT FROM PDF
        reader = PdfReader(file.file)
        pdf_text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pdf_text += extracted + "\n"


        prompt = f"""
You are an expert data analyst. Extract all relevant details from the following document and return them strictly in a well-formatted JSON object. 
If a field is empty, return null for that field.

Document Text: 
{pdf_text}

Please structure your JSON output in an easy-to-read and understandable format.
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

# INSERTING DIRECTLY INTO MONGODB
        insert_result = collection.insert_one(extracted_data)
        results.append(file.filename) 



print("\nAll PDFs processed and uploaded to MongoDB successfully!")

