# ISOLATED MICROSERVICE

import os
from pypdf import PdfReader
from dotenv import load_dotenv
from fastmcp import FastMCP
from tavily import TavilyClient

# LOADING API KEYS FROM .ENV
load_dotenv()

# INITIALIZING MCP SERVER
mcp = FastMCP("Dual Engine Search Server")

# INTIALIZING TAVILY CLIENT 
tavilyKey = os.getenv("TAVILY_API_KEY")
tavilyClient = TavilyClient(api_key = tavilyKey)

# IN MEMORY CACHE FOR UPLOADED PDFs
# it's a Python dictionary 
# if 10 questions asked about a PDF, it extracts the PDF text  on q1, and remembers it for remaining questions 
doc_cache = {}


# TOOL 1 : GREETING TOOL
# -----------------------------------
@mcp.tool()
def greeting_tool(name: str) -> str:
    # tool description
    """A simple greeting tool to verify that the AI client can access and execute tools."""
    return f"Hellooo {name}. Connection successful. The MCP server is active."


# TOOL 2 : TAVILY WEB SEARCH
# ----------------------------------
@mcp.tool()
def search_internet(query: str) -> str:
    # tool description
    """Surfs the internet using Tavily Search to get live information and external context."""

    try:
       # executing a basic context search 
       search_result = tavilyClient.get_search_context(query = query, max_results = 3) 
       return f"Internet search results for '{query}':\n\n{search_result}"
    
    except Exception as e:
        return f"An error occurred while searching the web: {str(e)}"
    

# TOOL 3 : PDF CONTENT RETRIEVAL
# --------------------------------------
@mcp.tool()
def query_pdf_context(file_path: str, question: str) -> str:
    # tool description
    """Queries the contents of the PDF to extract text or answer specific questions."""

    # checking if the file exists
    if not os.path.exists(file_path):
        return f"Error: No document found at path '{file_path}'. Make sure the file is uploaded correctly."

    # checking if the file is already extracted
    if file_path not in doc_cache:
        print(f"Extracting text from: {file_path}")
        extracted_text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    extracted_text += text + "\n" # appending to a growing string variable 
            
            # saving to cache
            doc_cache[file_path] = extracted_text
            print(f"Extraction complete for {file_path}.")
        except Exception as e:
            return f"Error reading PDF file: {str(e)}"
    
    # retrieving text from cache
    pdf_text = doc_cache[file_path]
    

    # returning the extracted text so Mistral can answer the specific question
    return f"Document source text:\n{pdf_text[:15000]}\n\nUser's question to answer based on the text: {question}"

    # why 15000?
    # - every AI model has a "context window" --> max amount of text it can hold in working memory at a time
    # - if the text from a PDF is too massive to process, API crashes  
    # - 15000 is a limit I kept so that the server can handle a minimal amount of text well
    # - but in massive production-grade application (ready for real-world business use), you don't blindly grab only 1st 15000 characters
    # - maybe the answer to user's question at the end of book --> instead you use RAG (Retrieval-Augmented Generation)
    # - RAG --> break down whole PDF into chunks, use search alg to find some chunks relevant to user's question, and send those chunks to AI



# RUNNING THE SERVER
if __name__ == "__main__":
    mcp.run()


   