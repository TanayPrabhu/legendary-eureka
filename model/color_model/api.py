import os
import sys
import time
import queue
import threading
import subprocess
import requests
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
import shutil
import base64

# Pipeline Imports
from dependency_manager import check_missing_deps, prompt_and_install

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🌟 REAL-TIME LOG INTERCEPTOR
# ==========================================
log_queue = queue.Queue()

class StreamCapture:
    def __init__(self, original_stream):
        self.original_stream = original_stream

    def write(self, data):
        self.original_stream.write(data)
        if data.strip():
            # Send to all SSE listeners
            log_queue.put(data)

    def flush(self):
        self.original_stream.flush()
        
    def isatty(self):
        if hasattr(self.original_stream, 'isatty'):
            return self.original_stream.isatty()
        return False

    def __getattr__(self, name):
        return getattr(self.original_stream, name)

# Replace stdout so we can capture prints
sys.stdout = StreamCapture(sys.stdout)

# ==========================================
# 🌟 GLOBAL APP STATE
# ==========================================
class AppState:
    is_translating = False
    current_job = None
    
app_state = AppState()

# ==========================================
# 🌟 FOLDER BROWSER API
# ==========================================
@app.get("/api/browse")
def browse_directory(path: str = None):
    try:
        if not path or path == "root":
            # For Windows, return drives
            drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
            if drives:
                return {"path": "root", "folders": [{"name": d, "path": d} for d in drives]}
            else:
                # Fallback to root (Linux/Mac or default env)
                path = "/"
        
        target_path = Path(path).resolve()
        
        if not target_path.exists() or not target_path.is_dir():
            return JSONResponse(status_code=400, content={"error": "Invalid directory"})

        folders = []
        for item in target_path.iterdir():
            if item.is_dir():
                try:
                    folders.append({"name": item.name, "path": str(item)})
                except PermissionError:
                    pass

        # Sort alphabetically
        folders.sort(key=lambda x: x["name"].lower())
        
        parent = str(target_path.parent) if target_path.parent != target_path else "root"
        
        return {
            "path": str(target_path),
            "parent": parent,
            "folders": folders
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==========================================
# 🌟 MODELS API
# ==========================================
@app.get("/api/models")
def list_models():
    models = []
    # User specified runs folder is in the root manga_translator directory
    # Since api.py is in model/color_model/, we step up two directories
    runs_dir = Path(__file__).resolve().parent.parent.parent / "runs"
    if runs_dir.exists() and runs_dir.is_dir():
        # Look for runs/*/weights/best.pt
        for model_dir in runs_dir.iterdir():
            if model_dir.is_dir():
                best_pt = model_dir / "weights" / "best.pt"
                if best_pt.exists():
                    display_name = model_dir.name
                    if display_name.startswith("train_"):
                        display_name = display_name[6:]
                    
                    models.append({
                        "name": display_name,
                        "path": str(best_pt.resolve())
                    })
    return {"models": models}

# ==========================================
# 🌟 FILE UPLOAD API (Drag & Drop)
# ==========================================
@app.post("/api/upload")
async def upload_images(files: list[UploadFile] = File(...)):
    temp_dir = Path("temp_inputs")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    first_image_b64 = None
    
    for idx, file in enumerate(files):
        file_path = temp_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Capture the first image for thumbnail preview
        if idx == 0:
            with open(file_path, "rb") as f:
                first_image_b64 = base64.b64encode(f.read()).decode('utf-8')
            
    return {
        "success": True, 
        "input_dir": str(temp_dir.resolve()),
        "thumbnail": first_image_b64,
        "count": len(files)
    }

# ==========================================
# 🌟 DEPENDENCY API
# ==========================================
@app.get("/api/deps/{pipeline}")
def check_pipeline_deps(pipeline: str):
    missing = check_missing_deps(pipeline)
    return {
        "pipeline": pipeline,
        "ready": len(missing) == 0,
        "missing": missing
    }

@app.post("/api/deps/{pipeline}/install")
def install_pipeline_deps(pipeline: str):
    missing = check_missing_deps(pipeline)
    if not missing:
        return {"success": True, "message": "All dependencies are already installed."}
    
    # Run pip install for all missing
    for dep in missing:
        pip_target = dep["pip_name"]
        print(f"Installing {pip_target}...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", pip_target],
                stdout=sys.stdout,
                stderr=subprocess.STDOUT
            )
            print(f"✅ {pip_target} installed successfully!")
        except subprocess.CalledProcessError as e:
            return JSONResponse(status_code=500, content={"error": f"Failed to install {pip_target}"})
            
    return {"success": True}

@app.post("/api/deps/{pipeline}/uninstall")
def uninstall_pipeline_deps(pipeline: str):
    from dependency_manager import uninstall_deps
    
    try:
        uninstall_deps(pipeline)
        
        # Shared Dependencies Logic (Ollama)
        if pipeline == "chinese":
            korean_missing = check_missing_deps("korean")
            if len(korean_missing) > 0:
                # Korean is NOT installed, so delete Ollama model
                subprocess.Popen(["ollama", "rm", "qwen2.5:3b"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif pipeline == "korean":
            chinese_missing = check_missing_deps("chinese")
            if len(chinese_missing) > 0:
                # Chinese is NOT installed, so delete Ollama model
                subprocess.Popen(["ollama", "rm", "qwen2.5:3b"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==========================================
# 🌟 TRANSLATION JOB LOGIC
# ==========================================
class TranslationRequest(BaseModel):
    input_dir: str
    output_img_dir: str
    output_json_dir: str
    model_path: str
    wipe_memory: bool = False

def run_translation_pipeline(req: TranslationRequest):
    app_state.is_translating = True
    app_state.current_job = req
    print("\n🚀 Starting Manga Translation Pipeline...")
    
    try:
        # Patch the model selection to avoid tkinter prompt inside the backend
        import japanese_predict
        japanese_predict.get_model_path = lambda: req.model_path
        import chinese_predict
        chinese_predict.get_model_path = lambda: req.model_path
        import korean_predict
        korean_predict.get_model_path = lambda: req.model_path

        # Lazy Import to prevent massive boot times
        from language_router import identify_manga_language, ensure_ollama_running

        # Step 1: Detect Language
        detected_language = identify_manga_language(req.input_dir)
        print(f"\n🌍 Winning Language: {detected_language.upper()}")

        if detected_language == "japanese":
            print("➡️ Routing to Japanese Pipeline...")
            from japanese_predict import process_japanese_manga
            process_japanese_manga(req.input_dir, req.output_img_dir, req.output_json_dir)
            
        elif detected_language == "chinese":
            print("➡️ Routing to Chinese Pipeline...")
            if len(check_missing_deps("chinese")) > 0:
                print("❌ Missing Chinese dependencies! Please install them from settings first.")
                return
                
            if not ensure_ollama_running():
                return

            if req.wipe_memory:
                from chinese_translator import reset_translation_context
                reset_translation_context()
                print("✅ AI Memory wiped!")

            from chinese_predict import process_chinese_manga
            process_chinese_manga(req.input_dir, req.output_img_dir, req.output_json_dir)
            
        elif detected_language == "korean":
            print("➡️ Routing to Korean Pipeline...")
            if len(check_missing_deps("korean")) > 0:
                print("❌ Missing Korean dependencies! Please install them from settings first.")
                return
                
            if not ensure_ollama_running():
                return

            if req.wipe_memory:
                from korean_translator import reset_translation_context
                reset_translation_context()
                print("✅ AI Memory wiped!")

            from korean_predict import process_korean_manhwa
            process_korean_manhwa(req.input_dir, req.output_img_dir, req.output_json_dir)
            
        else:
            print("❌ Could not confidently determine language. Exiting.")

    except Exception as e:
        print(f"\n❌ Pipeline Error: {e}")
    finally:
        app_state.is_translating = False
        app_state.current_job = None
        print("\n🏁 Translation Job Finished.")

@app.post("/api/translate/start")
def start_translation(req: TranslationRequest):
    if app_state.is_translating:
        return JSONResponse(status_code=400, content={"error": "A translation is already running."})

    import shared_state
    shared_state.stop_requested = False

    # Start in background thread
    thread = threading.Thread(target=run_translation_pipeline, args=(req,))
    thread.daemon = True
    thread.start()
    
    return {"success": True, "message": "Translation started"}

@app.get("/api/translate/status")
def get_translation_status():
    return {"is_translating": app_state.is_translating}

@app.post("/api/translate/stop")
def stop_translation():
    import shared_state
    shared_state.stop_requested = True
    return {"success": True, "message": "Stop requested"}

@app.get("/api/images/original")
def get_original_image(filename: str):
    from fastapi import Response
    if not app_state.current_job: return Response(status_code=404)
    path = Path(app_state.current_job.input_dir) / filename
    if path.exists() and path.is_file():
        return FileResponse(str(path))
    return Response(status_code=404)

@app.get("/api/images/translated")
def get_translated_image(filename: str):
    from fastapi import Response
    if not app_state.current_job: return Response(status_code=404)
    
    base_name, ext = os.path.splitext(filename)
    output_filename = f"{base_name}_output{ext}"
    
    path = Path(app_state.current_job.output_img_dir) / output_filename
    if path.exists() and path.is_file():
        return FileResponse(str(path), headers={"Cache-Control": "no-cache"})
    return Response(status_code=404)

@app.get("/api/translate/progress")
async def translation_progress(request: Request):
    """SSE Endpoint for streaming logs to frontend"""
    async def event_generator():
        while True:
            # If client disconnects
            if await request.is_disconnected():
                break

            try:
                # Grab a log message (block for a short time to avoid busy-waiting)
                log_msg = log_queue.get(timeout=0.2)
                yield {"data": log_msg}
            except queue.Empty:
                # Yield ping to keep connection alive
                yield {"event": "ping", "data": "ping"}

    return EventSourceResponse(event_generator())

# ==========================================
# 🌟 OLLAMA API
# ==========================================
@app.get("/api/ollama/status")
def get_ollama_status():
    try:
        response = requests.get("http://localhost:11434/", timeout=2)
        return {"running": response.status_code == 200}
    except requests.exceptions.RequestException:
        return {"running": False}

@app.post("/api/ollama/start")
def start_ollama():
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

# ==========================================
# 🌟 FRONTEND SERVING
# ==========================================
frontend_dist = Path("frontend/dist")

# If React build exists, mount it
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Allow API routes to pass through (they shouldn't hit this anyway due to priority, but just in case)
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"error": "Not found"})
            
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return "Frontend build not found. Run 'npm run build' in the frontend folder."

if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting MangaLens API Server on http://localhost:8000")
    print("   Please navigate to the URL in your browser.\n")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
