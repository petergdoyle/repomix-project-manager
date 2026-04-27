import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import manage_projects as mp
from pathlib import Path

app = FastAPI(title="Repomix Project Manager")

# Models
class ProjectCreate(BaseModel):
    name: str
    source: str
    ssh_key_path: Optional[str] = None

# API Endpoints
@app.get("/api/projects")
async def list_projects():
    return mp.get_project_list()

@app.post("/api/projects")
async def create_project(project: ProjectCreate):
    res = mp.create_project(project.name, project.source, project.ssh_key_path)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.post("/api/projects/{name}/build")
async def build_project(name: str):
    res = mp.build_project(name)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/api/projects/{name}/refresh")
async def refresh_project(name: str):
    res = mp.refresh_project(name)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/api/projects/{name}/clean")
async def clean_project(name: str):
    res = mp.clean_project(name)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/api/projects/{name}/archive")
async def archive_project(name: str):
    res = mp.archive_project(name)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res

@app.post("/api/projects/{name}/ssh-key")
async def upload_ssh_key(name: str, file: UploadFile = File(...)):
    content = await file.read()
    res = mp.set_project_ssh_key(name, key_content=content.decode('utf-8'))
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return res

@app.get("/api/projects/{name}/output")
async def get_output(name: str, download: bool = False):
    output_path = mp.PROJECTS_DIR / name / "outputs" / "repomix-output.md"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output not found. Run build first.")
    
    if download:
        return FileResponse(
            output_path, 
            filename=f"{name}-repomix.md",
            media_type="application/octet-stream"
        )
        
    return FileResponse(output_path)

@app.get("/api/projects/{name}/download/{filename}")
async def download_output(name: str, filename: str):
    output_path = mp.PROJECTS_DIR / name / "outputs" / "repomix-output.md"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Output not found. Run build first.")
    
    return FileResponse(
        output_path, 
        filename=filename,
        media_type="application/octet-stream"
    )

# Serve static files and index
@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open("web/index.html", "r") as f:
        return f.read()

# Mount static files if directory exists
if os.path.exists("web/static"):
    app.mount("/static", StaticFiles(directory="web/static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
