# MCP Server PDF & Web Search Conversational Chatbot
A full-stack, agentic AI application built utilizing the **Model Context Protocol (MCP)**. This chatbot acts as an intelligent orchestrator by using Mistral AI to autonomously decide whether to answer a user's prompt directly, search an uploaded PDF document, or fetch live information from the internet.

## Key Features
* The AI autonomously reads tool descriptions and calls tools based on semantic understanding of the user's prompt, rather than relying on strict keyword matching.
* Users can upload PDF documents via the UI file upload button. The backend securely caches the extracted text and allows the AI to answer specific questions about the document without re-parsing the file.
* Integrated with Tavily API, enabling the AI to summarize real-time web headlines and data.
* Dynamically injects the current date into the system prompt and prevets timeline hallucinations.
* A clean, mobile-framed HTML frontend styled with Bootstrap, featuring dynamic Markdown rendering for code blocks and rich text.

## Architecture Flow
The application isolates the tool execution from the AI logic using the MCP Stdio standard:

1. **Frontend (Browser):** User uploads a PDF or sends a message via the Bootstrap interface.
2. **FastAPI Orchestrator (`app.py`):** Receives the HTTP request, updates session states, and connects to the MCP Server as a background process using standard input/output.
3. **Mistral AI Routing:** The orchestrator asks Mistral to evaluate the user's message alongside the available MCP tools.
4. **MCP Server (`MCPServer.py`):** If Mistral requests a tool execution, the isolated FastMCP server runs the Python logic (PyPDF extraction or Tavily search) and returns the raw text data.
5. **Final Synthesis:** Mistral formats the tool data into a final readable response, and the frontend parses it into HTML using Marked.js.

## Tech Stack

**Frontend**
* HTML5, CSS3, Vanilla JavaScript
* Bootstrap 5 
* Marked.js (Markdown to HTML parsing)

**Backend Orchestrator**
* Python 3.x
* FastAPI & Uvicorn (Web Serving)
* Mistral AI Python SDK (LLM integration)
* MCP Core SDK (`mcp`) (Client session management)

**Tool Server**
* FastMCP (Anthropic's MCP Server Framework)
* PyPDF (Document text extraction)
* Tavily-Python (Live internet search)

## Setup and Installation

1. Clone the repository and set up a virtual environment

git clone <your-repo-url>

cd mcp-server-task

python -m venv venv

2. Activate the virtual environment
Windows:

.\venv\Scripts\activate

3. Install Dependencies

pip install fastapi uvicorn python-multipart mistralai mcp fastmcp pypdf tavily-python python-dotenv

4. Configure Environment Variables

Create a .env file in the root directory and add your API keys:

MISTRAL_API_KEY="your_mistral_api_key_here"

TAVILY_API_KEY="your_tavily_api_key_here"

## Running the Application
Because the FastAPI orchestrator is designed to automatically launch the MCP server in the background, only a single command is required to boot the entire stack:

python app.py

Once the server is running, open your web browser and navigate to:

http://127.0.0.1:5000

## Testing the System
Test the web search: "What are the latest tech headlines today?"

Test the PDF engine: Upload a document and ask: "Can you summarize the main points of this document?"

Test the greeting tool: "Hi, my name is [Your name]"

