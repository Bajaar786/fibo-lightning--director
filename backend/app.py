from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict
import httpx
import json
import os
import uvicorn
from dotenv import load_dotenv

# Import schemas and services
from models.schemas import SceneRequest, RefineRequest, GenerationResponse, RefineResponse, LightingParams
from services.fibo_client import FIBOClient
from services.refine_service import RefineService
from models.prompt_engine import PromptEngine
from utils.cache import SimpleCache

load_dotenv()

app = FastAPI(title="FIBO Lightning Director API")

# CORS - Allow Netlify and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "https://thriving-squirrel-bbbc9d.netlify.app",  # Your specific Netlify URL
        "https://*.netlify.app",
        "https://*.netlify.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys
FAL_KEY = os.getenv("FAL_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FAL_FIBO_MODEL = "fal-ai/fibo"

# Initialize services
fibo_client = FIBOClient(FAL_KEY) if FAL_KEY else None
refine_service = RefineService(GEMINI_API_KEY) if GEMINI_API_KEY else None
prompt_engine = PromptEngine(GEMINI_API_KEY) if GEMINI_API_KEY else None
generation_cache = SimpleCache(ttl_seconds=3600)

# Legacy models for backward compatibility
class LegacyLightingParams(BaseModel):
    key_intensity: int = 100
    key_temp: int = 5600  # Kelvin
    light_angle: int = 45
    fill_ratio: float = 0.5
    back_intensity: int = 30
    mood: str = "dramatic"

class LegacySceneRequest(BaseModel):
    prompt: str
    lighting: LegacyLightingParams
    camera_lens: str = "50mm"
    camera_fstop: float = 2.8
    hdr_enabled: bool = True
    seed: Optional[int] = None

# Legacy endpoint for backward compatibility
@app.post("/api/generate-legacy")
async def generate_scene_legacy(request: LegacySceneRequest):
    """Legacy endpoint for old frontend"""
    try:
        # Convert legacy request to new format
        from models.schemas import LightingParams as NewLightingParams, LightingType, CameraParams
        
        # Create new lighting setup from legacy params
        key_light = NewLightingParams(
            type=LightingType.KEY,
            intensity=request.lighting.key_intensity / 100.0,
            temperature=request.lighting.key_temp,
            direction_deg=request.lighting.light_angle,
            softness=0.3 if request.lighting.mood == "dramatic" else 0.7
        )
        
        # Create camera params
        camera = CameraParams(
            lens=request.camera_lens,
            f_stop=request.camera_fstop
        )
        
        # Create new scene request
        new_request = SceneRequest(
            prompt=request.prompt,
            lighting_setup=[key_light],
            camera=camera,
            hdr_enabled=request.hdr_enabled,
            seed=request.seed
        )
        
        # Use new endpoint logic
        return await generate_scene(new_request)
        
    except Exception as e:
        raise HTTPException(500, f"Legacy generation failed: {str(e)}")

# Routes
@app.get("/")
def home():
    return {
        "status": "ready",
        "features": ["hdr", "lighting_control", "cinematic_json", "refine"],
        "apis_configured": {
            "fal": FAL_KEY is not None,
            "gemini": GEMINI_API_KEY is not None
        },
        "services": {
            "fibo_client": fibo_client is not None,
            "refine_service": refine_service is not None,
            "prompt_engine": prompt_engine is not None
        }
    }

@app.post("/api/refine", response_model=RefineResponse)
async def refine_scene(request: RefineRequest):
    """Refine an existing scene with natural language instructions"""
    
    if not fibo_client or not refine_service:
        raise HTTPException(500, "API keys not configured")
    
    try:
        # 1. Refine the JSON based on instruction
        refined_json, changes = await refine_service.refine_json(
            request.previous_json,
            request.instruction
        )
        
        # 2. Generate new image with refined JSON
        generation_result = await fibo_client.generate_image(
            json_prompt=refined_json,
            hdr=request.hdr,
            seed=request.seed
        )
        
        if not generation_result["success"]:
            raise HTTPException(500, f"Generation failed: {generation_result.get('error')}")
        
        # 3. Return response
        return RefineResponse(
            success=True,
            image_url=generation_result["image_url"],
            refined_json=refined_json,
            instruction_applied=request.instruction,
            changes=changes
        )
        
    except Exception as e:
        raise HTTPException(500, f"Refinement failed: {str(e)}")

@app.post("/api/generate", response_model=GenerationResponse)
async def generate_scene(request: SceneRequest):
    """Professional scene generation endpoint"""
    
    # Validate API keys
    if not fibo_client or not prompt_engine:
        raise HTTPException(500, "API keys not configured")
    
    # Check cache first
    cache_key = request.dict()
    cached = generation_cache.get(cache_key)
    if cached:
        return GenerationResponse(**cached)
    
    try:
        # 1. Create FIBO JSON prompt
        fibo_json = await prompt_engine.create_fibo_json(request)
        
        # 2. Enhance for HDR if enabled
        if request.hdr_enabled:
            fibo_json = prompt_engine.enhance_for_hdr(fibo_json)
        
        # 3. Generate image with FIBO
        generation_result = await fibo_client.generate_image(
            json_prompt=fibo_json,
            hdr=request.hdr_enabled,
            size=request.output_size,
            seed=request.seed
        )
        
        if not generation_result["success"]:
            raise HTTPException(500, f"Generation failed: {generation_result.get('error')}")
        
        # 4. Prepare response
        response_data = {
            "success": True,
            "image_url": generation_result["image_url"],
            "request_id": generation_result["request_id"],
            "json_prompt": fibo_json,
            "metadata": {
                "lighting_setup": [light.dict() for light in request.lighting_setup],
                "camera": request.camera.dict(),
                "hdr": request.hdr_enabled,
                "style": request.style,
                "seed": generation_result["seed"],
                "size": generation_result["size"]
            },
            "processing_time_ms": generation_result["processing_time_ms"]
        }
        
        # Cache the result
        generation_cache.set(cache_key, response_data)
        
        return GenerationResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/api/presets/{preset_name}")
async def get_lighting_preset(preset_name: str):
    """Get pre-configured lighting setups"""
    from models.lighting import LightingPresets
    
    try:
        lights = LightingPresets.get_preset(preset_name)
        return {
            "preset": preset_name,
            "lights": [light.dict() for light in lights],
            "description": f"Cinematic {preset_name.replace('_', ' ')} lighting"
        }
    except:
        raise HTTPException(404, f"Preset '{preset_name}' not found")

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    import httpx
    
    checks = {
        "fal_api": FAL_KEY is not None,
        "gemini_api": GEMINI_API_KEY is not None,
        "cache_size": len(generation_cache.cache) if generation_cache else 0,
        "ready": FAL_KEY is not None and GEMINI_API_KEY is not None
    }
    
    # Test FAL API if key exists
    if FAL_KEY:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://fal.ai/api/health",
                    headers={"Authorization": f"Key {FAL_KEY}"},
                    timeout=5.0
                )
                checks["fal_accessible"] = response.status_code == 200
        except:
            checks["fal_accessible"] = False
    
    return {
        "status": "healthy" if all(checks.get(k, False) for k in ["fal_api", "gemini_api"]) else "degraded",
        "checks": checks
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
