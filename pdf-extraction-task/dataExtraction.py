import json
import argparse
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from mistralai.client import Mistral


# LOADING API KEY
load_dotenv() 
apiKey = os.getenv("MISTRAL_API_KEY")
model = "mistral-large-latest"
client = Mistral(api_key = apiKey)

pdf_folder = "PDFs"

# iterating through every file in  folder
for filename in os.listdir(pdf_folder):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(pdf_folder, filename)
        
        # matching output JSON filename (like S010_sample_print.pdf --> S010_sample_print.json)
        output_filename = filename.replace(".pdf", ".json")
        output_json_path = os.path.join(pdf_folder, output_filename)

        print(f"\n--- Processing {filename} ---")


    # EXTRACTING TEXT FROM PDF
        reader = PdfReader(pdf_path)
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

Please structure your JSON output exactly to match this schema:
{{
    "company": "Company's full name",
    "company address": "Company's address",
    "type of order": "Type of order",
    "customer company": "Customer's company full name (TO)",
    "customer telephone no": "Customer telephone no",
    "customer TRN": "Customer's TRN number",
    "document SO10 no": "Document's SO10 number",
    "document SO10 date": "Document's SO10 date",
    "cust LPO date": "Customer's LPO date",
    "expd. del date": "expected delivery date",
    "item table": [
        {{
            "SI NO/part no": "SI number of the item/part number of the item",
            "description": "Name or description of the item",
            "quantity": "Number of units ordered",
            "unit": "unit that the item is measured in",
            "AED rate": "price of the item when it's single quantity",
            "AED amount": "total price of the item"
        }}
    ],
    "gross total": "gross total of the order",
    "AED net total": "net total of the order",
    "total amount in text": "the net total in text",
    "prepared by": "prepared by",
    "checked by": "checked by",
    "authorized by": "authorized by"
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

# CONVERTING RESPONSE STRING BACK INTO PYTHON 
        extracted_data = json.loads(response.choices[0].message.content)


# SAVING RESULTS INTO JSON FILE
        with open(output_json_path, 'w') as json_file:
            json.dump(extracted_data, json_file, indent = 4)

        print(f"\nData succesfully saved into {output_json_path}")

print("\nAll PDFs processed successfully!")



    







