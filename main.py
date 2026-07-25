import subprocess
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="AI Code Assistant API",
    description="Unified API interface for Code Indexer, Retriever, Chat, and Bug Finder."
)

# --- Request Models ---

class FileRequest(BaseModel):
    filepath: str

class QueryRequest(BaseModel):
    query: str

# --- Helper Function ---

def run_script(script_name: str, args: list[str]) -> str:
    """Runs a Python script as a subprocess and captures output."""
    try:
        command = [sys.executable, script_name] + args
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or result.stdout.strip()
            raise Exception(error_msg)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Execution of {script_name} timed out.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API Endpoints ---

@app.get("/")
def root():
    return {"status": "online", "message": "AI Code Assistant API is running!"}

@app.post("/api/index")
def index_code(request: FileRequest):
    """Index a file or directory into ChromaDB."""
    output = run_script("indexer.py", ["--file", request.filepath])
    return {"status": "success", "output": output}

@app.post("/api/retrieve")
def retrieve_code(request: QueryRequest):
    """Retrieve relevant code snippets based on query."""
    output = run_script("retriever.py", ["--query", request.query])
    return {"status": "success", "output": output}

@app.post("/api/chat")
def chat_code(request: QueryRequest):
    """Ask a question about the indexed codebase."""
    output = run_script("chat.py", ["--query", request.query])
    return {"status": "success", "output": output}

@app.post("/api/bug-finder")
def find_bugs(request: FileRequest):
    """Run static analysis + LLM bug identification on a Python file."""
    output = run_script("bug_finder.py", ["--file", request.filepath])
    return {"status": "success", "output": output}