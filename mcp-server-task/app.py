# BRIDGE BETWEEN FRONT END AND BACK END 
# ORCHESTRATOR --> serves the HTML page to user, catches files uploaded, manages conversations, translates between Mistral and background MCP script, and handles tool routing.

import os
import json
from mistralai.client import Mistral
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import HTMLResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client # these 2 allow this script to run MCPServer.py in the 
                                          # background and control it directly
from datetime import datetime # so that Mistral is up to date with the timeline

load_dotenv()

app = FastAPI(title = "MCP Web Bridge")

# directory to save uploaded files 
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok = True)

# initializing Mistral client
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    
mistral_client = Mistral(api_key = MISTRAL_API_KEY)
model_name = "mistral-large-latest"

# tracking the active filename globally for this session so I don't lose state across HTTP requests 
current_session = {
    "file_path": None,
    "file_name": "No file uploaded"
}

# structured input model utilizing Pydantic to ensure incoming requests contain exactly 
# what they need (message and name).
class ChatRequest(BaseModel):
    message: str
    name: str = "User"

# configuration to launch MCP Server as a background process
# instructs OS exactly how to boot up the tool server whenever an operation needs to run
server_params = StdioServerParameters(
    command = "python",
    args = ["MCPServer.py"]
)

# ROUTE --> SERVING WEB APP UI
# When opening the URL, FastAPI drops everything and opens raw index.html text and returns it to 
# the browser window
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html", "r", encoding = "utf-8") as f:
        return f.read() 
    

# ROUTE --> HANDLING FILE UPLOAD REQUESTS
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code = 400, detail = "Only PDF files allowed !!")
    
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    
    # saving the uploaded file stream on a blank target file 
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    # notes the file path into active session memory so the chat loop knows it's there
    current_session["file_path"] = file_path
    current_session["file_name"] = file.filename
    
    return {"message": "File uploaded successfully", "filename": file.filename}


# ROUTE --> CORE AGENTIC LOOP
# with this approach, any number of tools can be added in the future 
@app.post("/chat")
async def chat(request: ChatRequest):
    user_message = request.message.strip()
    
    if not user_message:
        raise HTTPException(status_code = 400, detail = "Message cannot be empty..")

    # dynamically grabbing the exact current date
    current_date = datetime.now().strftime("%A, %B %d, %Y") # now Mistral has the correct year context

    # If a file path is stored inside current_session, the script injects an 
    # added target rule: "IMPORTANT: The user has ....."
    system_instruction = f"You are a helpful AI assistant. Today's date is {current_date}. You have access to external tools to search the internet or read uploaded PDFs. Use them if necessary."
    
    # injecting the document context if a file is uploaded
    if current_session.get("file_path"):
        uploaded_file = current_session["file_name"]
        system_instruction += f"\n\nIMPORTANT: The user has currently uploaded a document named '{uploaded_file}'. If they ask about 'this document', 'the text', or 'the file', they are referring to '{uploaded_file}'. You must use the query_pdf_context tool to answer their questions about it."

    # setting up conversation history for Mistral
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_message}
    ]


    # opening a secure pipeline to MCPServer.py
    # launches MCPServer.py as a backgroud process
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # initializing connection
            await session.initialize()

            # asking MCP Server what tools are available
            mcp_tools_list = await session.list_tools()
            
            # formatting those tools so Mistral can read them
            mistral_tools = [{
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in mcp_tools_list.tools]

            # sending the user's message and the available tools to Mistral
            response = mistral_client.chat.complete(
                model = model_name,
                messages = messages,
                tools = mistral_tools,
                tool_choice = "auto"    # IMPORTANT cuz now Mistral is allowed to connect the dots and choose which tool to call
                                        # Mistral reads the tool descriptions to choose
            )

            response_message = response.choices[0].message
            messages.append(response_message) # saving Mistral's thought process

            tool_used_ui_string = "None"

            # checking --> did Mistral decide it needs to use a tool?
            # if Mistral requests a tool call (eg: search_internet)the code traps that request
            # if it targets query_pdf_context, script injects file_path
            # it then sends the execution call to the background server
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # If Mistral wants to read PDF, secretly feeding it the active file path
                    if tool_name == "query_pdf_context" and current_session["file_path"]:
                        tool_args["file_path"] = current_session["file_path"]

                    # executing the tool securely on MCPServer
                    tool_result = await session.call_tool(tool_name, tool_args)
                    
                    # extracting raw text from MCP server's response
                    result_text = "".join([c.text for c in tool_result.content if hasattr(c, 'text')])

                    # tool's output back to Mistral
                    messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": result_text,
                        "tool_call_id": tool_call.id
                    })
                    
                    tool_used_ui_string = f"{tool_name}(...)"

                # asking Mistral to generate a final response using new tool data
                final_response = mistral_client.chat.complete(
                    model = model_name,
                    messages = messages
                )
                final_text = final_response.choices[0].message.content
            
            else:
                # otherwise Mistral decided no tool was needed, so it answers normally
                final_text = response_message.content

            return {"tool": tool_used_ui_string, "response": final_text}
        

if __name__ == '__main__':
    import uvicorn
    # running the app locally on port 5000
    uvicorn.run(app, host = "127.0.0.1", port = 5000)


