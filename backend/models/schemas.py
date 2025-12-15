from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum

class LightingType(str, Enum):
    KEY = "key"
    FILL = "fill"
    BACK = "back"
    RIM = "rim"
    PRACTICAL = "practical"

class CameraLens(str, Enum):
    WIDE_24MM = "24mm"
    NORMAL_50MM = "50mm"
    PORTRAIT_85MM = "85mm"
    TELE_135MM = "135mm"
    CINEMA_35MM = "35mm"

class LightingParams(BaseModel):
    """Professional lighting parameters"""
    type: LightingType = LightingType.KEY
    intensity: float = Field(1.0, ge=0.0, le=2.0)  # 0-200%
    temperature: int = Field(5600, ge=1000, le=10000)  # Kelvin
    direction_deg: int = Field(45, ge=0, le=360)
    distance: float = Field(1.0, ge=0.1, le=10.0)  # Relative units
    softness: float = Field(0.5, ge=0.0, le=1.0)
    
    def to_description(self) -> str:
        """Convert to natural language for prompt"""
        temp_desc = "warm" if self.temperature < 4000 else "cool" if self.temperature > 6000 else "neutral"
        return f"{self.type.value} light at {self.direction_deg} degrees, {self.intensity*100:.0f}% intensity, {temp_desc} ({self.temperature}K)"

class CameraParams(BaseModel):
    """Cinematic camera parameters"""
    lens: CameraLens = CameraLens.NORMAL_50MM
    f_stop: float = Field(2.8, ge=1.2, le=16.0)
    focal_distance: float = Field(5.0, ge=0.1, le=100.0)
    angle: str = "eye-level"
    movement: Optional[str] = None  # "dolly", "pan", "static"
    
    def to_description(self) -> str:
        return f"{self.lens.value} lens at f/{self.f_stop}, {self.angle} shot"

class SceneRequest(BaseModel):
    """Complete scene generation request"""
    prompt: str = Field(..., min_length=5, max_length=500)
    lighting_setup: List[LightingParams] = Field(default_factory=list)
    camera: CameraParams = Field(default_factory=CameraParams)
    hdr_enabled: bool = True
    style: str = "cinematic"
    seed: Optional[int] = None
    output_size: str = "1024x1024"  # or "768x768", "1536x1536"
    
    def validate_lighting(self):
        """Ensure at least one key light"""
        if not any(light.type == LightingType.KEY for light in self.lighting_setup):
            # Add default key light if none provided
            self.lighting_setup.append(LightingParams(type=LightingType.KEY))
        return self

class RefineRequest(BaseModel):
    """Request to refine an existing scene"""
    previous_json: Dict
    instruction: str = Field(..., min_length=2, max_length=200)
    hdr: bool = True
    seed: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "previous_json": {
                    "subject": "a detective in an office",
                    "lighting": {"intensity": 1.0, "temperature": 5600}
                },
                "instruction": "make it darker and moodier",
                "hdr": True
            }
        }

class GenerationResponse(BaseModel):
    """Response model for generation"""
    success: bool
    image_url: str
    request_id: str
    json_prompt: dict
    metadata: dict
    processing_time_ms: int

class RefineResponse(BaseModel):
    """Response from refine endpoint"""
    success: bool
    image_url: str
    refined_json: Dict
    instruction_applied: str
    changes: Dict  # What was modified
