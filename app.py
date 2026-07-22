import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from retriever import parse_markdown_schema, parse_json_schema, SchemaRetriever

app = FastAPI(title="Text-to-SQL Table Retrieval API")

# Store retrievers: schema_id -> SchemaRetriever
loaded_schemas = {}

# Load default schema
default_schema_path = "schema_design.md"
if os.path.exists(default_schema_path):
    with open(default_schema_path, "r", encoding="utf-8") as f:
        md_content = f.read()
    try:
        default_tables = parse_markdown_schema(md_content)
        loaded_schemas["default"] = SchemaRetriever(default_tables)
    except Exception as e:
        print(f"Error loading default schema: {e}")

class QueryRequest(BaseModel):
    question: str
    schema_id: Optional[str] = "default"

@app.get("/schema/default")
def get_default_schema():
    if "default" not in loaded_schemas:
        raise HTTPException(status_code=404, detail="Default schema not loaded")
    
    retriever = loaded_schemas["default"]
    return {
        "tables": [t.to_dict() for t in retriever.tables]
    }

@app.post("/schema/upload")
async def upload_schema(file: UploadFile = File(...)):
    content = await file.read()
    content_str = content.decode("utf-8")
    
    filename = file.filename.lower()
    try:
        if filename.endswith(".json"):
            tables = parse_json_schema(content_str)
        elif filename.endswith(".md") or filename.endswith(".txt"):
            tables = parse_markdown_schema(content_str)
        else:
            raise HTTPException(status_code=400, detail="Unsupported schema file format. Please upload JSON or Markdown (.md) files.")
        
        if not tables:
            raise HTTPException(status_code=400, detail="No tables found in the schema file.")
            
        schema_id = str(uuid.uuid4())
        # Instantiate model for custom schema
        loaded_schemas[schema_id] = SchemaRetriever(tables)
        
        return {
            "schema_id": schema_id,
            "filename": file.filename,
            "tables": [t.to_dict() for t in tables]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse schema: {str(e)}")

@app.post("/query")
def run_query(request: QueryRequest):
    schema_id = request.schema_id or "default"
    if schema_id not in loaded_schemas:
        raise HTTPException(status_code=404, detail=f"Schema with ID '{schema_id}' not found.")
        
    retriever = loaded_schemas[schema_id]
    try:
        results = retriever.search(request.question)
        return {
            "query": request.question,
            "schema_id": schema_id,
            "tables": [{"name": name, "score": float(score)} for name, score in results]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

# Mount static files to serve frontend
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # Start on host 0.0.0.0 and port from environment variable for container routing
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
