# PDF Data Extractor
A lightweight, full-stack web application designed to automate the extraction of unstructured data from PDF documents (like sales invoices) and store the formatted results in a cloud database (MongoDB).

## Features
* A sleek, dark-themed web UI built with Bootstrap 5 for uploading multiple PDFs simultaneously
* Integrates the Mistral AI API to intelligently analyze raw PDF text and strictly output well-formatted JSON structures
* Automatically pushes the extracted JSON documents to a MongoDB Atlas cluster for long-term, scalable storage.

## Tech Stack
* **Frontend:** HTML5, Custom CSS, Bootstrap 5, JavaScript
* **Backend:** Python, FastAPI, Uvicorn
* **AI & Processing:** Mistral AI, pypdf
* **Database:** MongoDB Atlas (pymongo)

## Setup & Installation
1. Clone repo:
git clone <your-repo-url>

cd pdf-extraction-webpage

2. Activate the virtual environment:
For Windows Command Prompt -->

venv\Scripts\activate.bat

3. Install dependencies:
pip install fastapi uvicorn python-multipart pypdf mistralai pymongo python-dotenv

4. Configure Environment Variables:
Create a .env file in the root directory and add your credentials:

MISTRAL_API_KEY=your_mistral_api_key_here

MONGO_URI=mongodb+srv://<username>:<password>@cluster.mongodb.net/?retryWrites=true&w=majority

## Usage
Start the FastAPI server using Uvicorn:

uvicorn main:app --reload

Open your browser and navigate to http://127.0.0.1:8000. Select your PDFs, click Extract Data!, and the parsed JSON will be securely uploaded to your MongoDB cluster.

