"""Core/api/server.py — FastAPI REST API for Mr.Holmes OSINT."""
from __future__ import annotations
import asyncio
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from Core.api.auth import authenticate, create_token, verify_token
from Core.plugins.manager import PluginManager
from Core.config.settings import settings
from Core.engine.autonomous_agent import StagedProfiler

app = FastAPI(title="Mr.Holmes OSINT API", version="1.0.0")
# auto_error=False so that missing credentials yield 403 (Forbidden) rather
# than FastAPI's default 401 — distinguishes "no token" from "bad token".
security = HTTPBearer(auto_error=False)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

class TargetRequest(BaseModel):
    target: str
    target_type: str = "username"  # username, email, phone, domain
    max_depth: int = 1

class PluginCheckRequest(BaseModel):
    plugin_name: str
    target: str
    target_type: str = "username"

# --- Auth dependency ---
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Missing/empty credentials → 403 Forbidden (no token supplied at all)
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=403, detail="Not authenticated")
    user = verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# --- Endpoints ---
@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Mr.Holmes OSINT API"}

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    user = authenticate(req.username, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(user)
    return LoginResponse(access_token=token, role=user["role"])

@app.get("/api/plugins")
async def list_plugins(user: dict = Depends(get_current_user)):
    manager = PluginManager()
    manager.discover_plugins()
    return {
        "plugins": [
            {
                "name": p.name,
                "stage": getattr(p, "stage", 1),
                "requires_api_key": p.requires_api_key,
                "target_types": getattr(p, "target_types", []),
            }
            for p in manager.plugins
        ]
    }

@app.post("/api/plugins/check")
async def plugin_check(req: PluginCheckRequest, user: dict = Depends(get_current_user)):
    manager = PluginManager()
    manager.discover_plugins()
    plugin = next((p for p in manager.plugins if p.name == req.plugin_name), None)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Plugin '{req.plugin_name}' not found")
    plugin.api_key = settings.get_plugin_key(plugin.name)
    result = await plugin.check(req.target, req.target_type)
    return {
        "plugin": plugin.name,
        "target": req.target,
        "is_success": result.is_success,
        "data": result.data,
        "error": result.error_message,
    }

@app.post("/api/profile/run")
async def run_profiler(req: TargetRequest, user: dict = Depends(get_current_user)):
    manager = PluginManager()
    manager.discover_plugins()
    plugins = manager.plugins
    for p in plugins:
        p.api_key = settings.get_plugin_key(p.name)
    profiler = StagedProfiler(max_depth=req.max_depth, plugins=plugins)
    result = await profiler.run_staged(req.target, req.target_type, plugins=plugins)
    return {
        "target": req.target,
        "target_type": req.target_type,
        "nodes": result.get("nodes", []),
        "edges": result.get("edges", []),
        "plugin_results": result.get("plugin_results", []),
        "stats": {
            "node_count": len(result.get("nodes", [])),
            "edge_count": len(result.get("edges", [])),
            "result_count": len(result.get("plugin_results", [])),
        }
    }

@app.get("/api/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user
