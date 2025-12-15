"""
Intelligent prompt engineering for FIBO JSON
"""
import json
from typing import Dict, List
import httpx
import os
from models.schemas import SceneRequest, LightingParams, CameraParams

class PromptEngine:
    """Convert scene parameters to optimized FIBO JSON"""
    
    def __init__(self, gemini_api_key: str):
        self.gemini_api_key = gemini_api_key
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_api_key}"
    
    async def create_fibo_json(self, request: SceneRequest) -> Dict:
        """Create optimized FIBO JSON from scene request"""
        
        # Use Gemini for intelligent JSON creation
        prompt_text = self._build_prompt_text(request)
        
        try:
            # Try Gemini first
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.gemini_url,
                    json={
                        "contents": [{
                            "parts": [{"text": prompt_text}]
                        }]
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    json_text = result["candidates"][0]["content"]["parts"][0]["text"]
                    # Clean JSON from response
                    json_text = json_text.strip().replace('```json', '').replace('```', '')
                    return json.loads(json_text)
        except:
            pass
        
        # Fallback: Generate JSON ourselves
        return self._create_fallback_json(request)
    
    def _build_prompt_text(self, request: SceneRequest) -> str:
        """Build prompt for Gemini"""
        
        lighting_desc = "\n".join([
            f"- {light.to_description()}" 
            for light in request.lighting_setup
        ])
        
        return f"""
        You are a professional cinematographer and AI prompt engineer.
        Create a structured JSON for FIBO image generation with these exact parameters:
        
        SCENE: {request.prompt}
        STYLE: {request.style}
        
        LIGHTING SETUP:
        {lighting_desc}
        
        CAMERA: {request.camera.to_description()}
        HDR: {'Yes, 16-bit color, high dynamic range' if request.hdr_enabled else 'No'}
        
        Create a JSON with these exact keys:
        {{
            "subject": "detailed subject description",
            "environment": "detailed environment description",
            "lighting": {{
                "setup": "description of lighting setup",
                "mood": "lighting mood",
                "quality": "hard/soft",
                "contrast": "high/medium/low"
            }},
            "camera": {{
                "lens": "lens description",
                "aperture": "f-stop value",
                "shot_type": "type of shot",
                "composition": "composition notes"
            }},
            "style_attributes": {{
                "dynamic_range": "hdr" or "standard",
                "color_palette": ["primary", "secondary", "accent colors"],
                "texture": "description of textures"
            }},
            "technical": {{
                "render_quality": "high",
                "detail_level": "ultra detailed"
            }}
        }}
        
        Return ONLY the JSON object, no other text.
        """
    
    def _create_fallback_json(self, request: SceneRequest) -> Dict:
        """Create JSON without Gemini"""
        
        # Extract key light
        key_lights = [l for l in request.lighting_setup if l.type.value == "key"]
        key_light = key_lights[0] if key_lights else LightingParams()
        
        return {
            "subject": request.prompt.split(",")[0] if "," in request.prompt else request.prompt,
            "environment": "professional cinematic scene",
            "lighting": {
                "setup": f"{len(request.lighting_setup)}-point lighting",
                "mood": "dramatic" if key_light.intensity > 1.0 else "subtle",
                "quality": "hard" if key_light.softness < 0.3 else "soft",
                "contrast": "high" if len(request.lighting_setup) < 2 else "medium",
                "color_temperature": f"{key_light.temperature}K",
                "direction": f"{key_light.direction_deg} degrees"
            },
            "camera": {
                "lens": request.camera.lens.value,
                "aperture": request.camera.f_stop,
                "shot_type": request.camera.angle,
                "composition": "rule of thirds, cinematic framing"
            },
            "style_attributes": {
                "dynamic_range": "hdr" if request.hdr_enabled else "standard",
                "color_palette": ["dark", "contrasted", "cinematic"],
                "texture": "film grain, realistic textures",
                "color_grade": "cinematic"
            },
            "technical": {
                "render_quality": "high",
                "detail_level": "ultra detailed",
                "format": "16-bit" if request.hdr_enabled else "8-bit"
            }
        }
    
    def enhance_for_hdr(self, json_prompt: Dict) -> Dict:
        """Enhance JSON for HDR generation"""
        if "style_attributes" not in json_prompt:
            json_prompt["style_attributes"] = {}
        
        json_prompt["style_attributes"].update({
            "dynamic_range": "hdr",
            "color_depth": "16-bit",
            "highlight_recovery": 0.8,
            "shadow_detail": 0.3,
            "tonemapping": "aces",
            "max_nits": 1000
        })
        
        return json_prompt