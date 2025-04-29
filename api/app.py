import os
import sys
import uuid
import time
import shutil
import logging
import tempfile
import asyncio  
from pathlib import Path
from typing import List, Dict, Optional

import uvicorn
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# Import the PDF processor
sys.path.append(str(Path(__file__).parent.parent))
from preprocessing.preprocess import PDFProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("api_server.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("api_server")

# Create FastAPI app
app = FastAPI(
    title="PDF Processing API",
    description="API for extracting text from PDF documents",
    version="1.0.0",
)

# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        current_time = time.time()
        
        # Clean up old entries
        self.requests = {k: v for k, v in self.requests.items() 
                        if current_time - v[-1] < self.window_seconds}
        
        # Check if client exceeded rate limit
        if client_ip in self.requests:
            if len(self.requests[client_ip]) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."}
                )
            self.requests[client_ip].append(current_time)
        else:
            self.requests[client_ip] = [current_time]
        
        return await call_next(request)

app.add_middleware(RateLimitMiddleware, max_requests=5, window_seconds=10)

# Create directory for storing uploads and results
UPLOAD_DIR = Path("./uploads")
RESULTS_DIR = Path("./results")
UPLOAD_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# In-memory task storage
tasks = {}

class TaskStatus(BaseModel):
    """Model for task status updates"""
    task_id: str
    status: str  # "pending", "processing", "completed", "failed"
    progress: int  # 0-100
    result_file: Optional[str] = None
    message: Optional[str] = None
    scheduled_for_deletion: bool = False  # Add this line

class ProcessingOptions(BaseModel):
    """Model for PDF processing options"""
    output_format: str = "csv"
    extraction_method: str = "auto"
    include_metadata: bool = True
    text_only: bool = False

# Routes for web interface
@app.get("/")
async def root(request: Request):
    """Render the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

# API endpoints
@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    output_format: str = Form("csv"),
    extraction_method: str = Form("auto"),
    include_metadata: bool = Form(True),
    text_only: bool = Form(False),
):
    """
    Handle file upload and start processing in the background
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate unique ID for this task
    task_id = str(uuid.uuid4())
    
    # Save uploaded file
    upload_path = UPLOAD_DIR / f"{task_id}.pdf"
    result_path = RESULTS_DIR / f"{task_id}.{output_format}"
    
    try:
        with open(upload_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    
    # Initialize task status
    tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        progress=0,
        message="Preparing to process PDF"
    )
    
    # Start processing in background
    background_tasks.add_task(
        process_pdf,
        task_id,
        upload_path,
        result_path,
        output_format,
        extraction_method,
        include_metadata,
        text_only
    )
    
    return {"task_id": task_id, "message": "PDF uploaded successfully. Processing started."}

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """Check the status of a processing task"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    return tasks[task_id]

@app.get("/api/download/{task_id}")
async def download_result(task_id: str):
    """Download the processed result file"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task = tasks[task_id]
    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Processing not yet completed")
    
    if not task.result_file or not os.path.exists(task.result_file):
        raise HTTPException(status_code=404, detail="Result file not found")
    
    return FileResponse(
        path=task.result_file,
        filename=os.path.basename(task.result_file),
        media_type=_get_media_type(task.result_file)
    )

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, background_tasks: BackgroundTasks):
    """Delete a task and its associated files"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    try:
        # Mark for deletion without removing from tasks dict yet
        tasks[task_id].scheduled_for_deletion = True
        
        # Schedule actual deletion for later (e.g., 5 minutes)
        background_tasks.add_task(delayed_delete_task, task_id, delay=300)
        
        return {"message": f"Task {task_id} scheduled for deletion"}
    except Exception as e:
        logger.error(f"Error scheduling task deletion {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error scheduling task deletion: {str(e)}")

async def delayed_delete_task(task_id: str, delay: int):
    """Delete a task after a delay"""
    await asyncio.sleep(delay)
    
    try:
        if task_id not in tasks:
            return
        
        # Delete uploaded file
        upload_path = UPLOAD_DIR / f"{task_id}.pdf"
        if upload_path.exists():
            upload_path.unlink()
        
        # Delete result file if exists
        task = tasks[task_id]
        if task.result_file and os.path.exists(task.result_file):
            os.unlink(task.result_file)
        
        # Remove task from memory
        del tasks[task_id]
        
        logger.info(f"Task {task_id} deleted after delay")
    except Exception as e:
        logger.error(f"Error in delayed deletion of task {task_id}: {str(e)}")

# Background processing function
async def process_pdf(
    task_id: str,
    pdf_path: Path,
    result_path: Path,
    output_format: str,
    extraction_method: str,
    include_metadata: bool,
    text_only: bool
):
    """Process PDF in the background and update task status"""
    logger.info(f"Processing PDF {pdf_path} with task ID {task_id}")
    
    try:
        # Update task status to processing
        tasks[task_id].status = "processing"
        tasks[task_id].progress = 10
        tasks[task_id].message = "Processing started"
        
        # Initialize processor
        processor = PDFProcessor(
            output_format=output_format,
            chunk_size=1000,
            max_workers=2,  # Lower worker count for server environment
            extraction_method=extraction_method,
            include_metadata=include_metadata,
            text_only=text_only
        )
        
        # Process file with progress updates
        tasks[task_id].progress = 20
        tasks[task_id].message = "Validating PDF"
        
        # Process the file
        result_file = processor.process_file(pdf_path, str(result_path))
        
        # Check if processing was successful
        if result_file and os.path.exists(result_file):
            tasks[task_id].status = "completed"
            tasks[task_id].progress = 100
            tasks[task_id].result_file = result_file
            tasks[task_id].message = "Processing completed successfully"
            logger.info(f"Task {task_id} completed successfully")
        else:
            tasks[task_id].status = "failed"
            tasks[task_id].progress = 0
            tasks[task_id].message = "Processing failed - no output file generated"
            logger.error(f"Task {task_id} failed - no output file generated")
            
    except Exception as e:
        logger.error(f"Error processing PDF for task {task_id}: {str(e)}")
        tasks[task_id].status = "failed"
        tasks[task_id].progress = 0
        tasks[task_id].message = f"Processing failed: {str(e)}"
    finally:
        # Clean up the temporary file
        try:
            if os.path.exists(pdf_path):
                os.unlink(pdf_path)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary file {pdf_path}: {str(e)}")

def _get_media_type(file_path: str) -> str:
    """Determine the media type based on file extension"""
    if file_path.endswith('.csv'):
        return 'text/csv'
    elif file_path.endswith('.json'):
        return 'application/json'
    elif file_path.endswith('.parquet'):
        return 'application/octet-stream'
    else:
        return 'text/plain'

# Cleanup task to remove old tasks and files
@app.on_event("startup")
async def startup_event():
    """Clean up old files on startup"""
    try:
        # Clear old files from upload and results directories
        for file_path in UPLOAD_DIR.glob('*'):
            if file_path.is_file() and (time.time() - file_path.stat().st_mtime) > 3600:  # 1 hour
                file_path.unlink()
                
        for file_path in RESULTS_DIR.glob('*'):
            if file_path.is_file() and (time.time() - file_path.stat().st_mtime) > 3600:  # 1 hour
                file_path.unlink()
                
        logger.info("Cleaned up old files during startup")
    except Exception as e:
        logger.error(f"Error during startup cleanup: {str(e)}")

# Run the application when executed directly
if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)