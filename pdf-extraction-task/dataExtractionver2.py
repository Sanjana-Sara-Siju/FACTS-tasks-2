import json
import argparse
import os
from dotenv import load_dotenv
from pypdf import PdfReader
from mistralai.client import Mistral


# LOADING API KEY
load_dotenv() 
apiKey = os.getenv("MISTRAL_API_KEY")
model = "mistral-small-latest"
client = Mistral(api_key = apiKey)

pdf_folder = "PDFs"

# iterating through every file in folder
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


# SAVING RESULTS INTO JSON FILE
        with open(output_json_path, 'w') as json_file:
            json.dump(extracted_data, json_file, indent = 4)

        print(f"\nData succesfully saved into {output_json_path}")

print("\nAll PDFs processed successfully!")

