"""
Cinematic lighting calculations and presets
"""
import math
from typing import Dict, List
from models.schemas import LightingParams, LightingType

class LightingPhysics:
    """Calculate realistic lighting interactions"""
    
    @staticmethod
    def calculate_falloff(intensity: float, distance: float, falloff_type: str = "inverse_square") -> float:
        """Calculate light intensity falloff"""
        if falloff_type == "inverse_square":
            return intensity / (distance ** 2)
        elif falloff_type == "linear":
            return intensity * max(0, 1 - distance/10)
        else:  # no falloff
            return intensity
    
    @staticmethod
    def mix_light_colors(lights: List[LightingParams]) -> str:
        """Calculate mixed color temperature from multiple lights"""
        if not lights:
            return "5600K neutral"
        
        # Weighted average by intensity
        total_intensity = sum(light.intensity for light in lights)
        if total_intensity == 0:
            return "5600K neutral"
        
        avg_temp = sum(light.temperature * light.intensity for light in lights) / total_intensity
        
        # Describe the mixed temperature
        if avg_temp < 3500:
            desc = "warm orange"
        elif avg_temp < 4500:
            desc = "warm white"
        elif avg_temp < 5500:
            desc = "neutral white"
        elif avg_temp < 6500:
            desc = "cool white"
        else:
            desc = "cool blue"
        
        return f"{int(avg_temp)}K {desc}"

class LightingPresets:
    """Pre-configured cinematic lighting setups"""
    
    @staticmethod
    def film_noir() -> List[LightingParams]:
        return [
            LightingParams(
                type=LightingType.KEY,
                intensity=0.8,
                temperature=3200,
                direction_deg=45,
                softness=0.3
            ),
            LightingParams(
                type=LightingType.FILL,
                intensity=0.2,
                temperature=3200,
                direction_deg=315,
                softness=0.7
            ),
            LightingParams(
                type=LightingType.BACK,
                intensity=0.1,
                temperature=2800,
                direction_deg=180,
                softness=0.1
            )
        ]
    
    @staticmethod
    def golden_hour() -> List[LightingParams]:
        return [
            LightingParams(
                type=LightingType.KEY,
                intensity=1.2,
                temperature=2800,
                direction_deg=30,
                softness=0.6
            ),
            LightingParams(
                type=LightingType.FILL,
                intensity=0.4,
                temperature=3800,
                direction_deg=330,
                softness=0.8
            ),
            LightingParams(
                type=LightingType.RIM,
                intensity=0.6,
                temperature=2200,
                direction_deg=150,
                softness=0.2
            )
        ]
    
    @staticmethod
    def studio_portrait() -> List[LightingParams]:
        return [
            LightingParams(
                type=LightingType.KEY,
                intensity=1.0,
                temperature=5600,
                direction_deg=45,
                softness=0.7
            ),
            LightingParams(
                type=LightingType.FILL,
                intensity=0.5,
                temperature=5600,
                direction_deg=315,
                softness=0.9
            ),
            LightingParams(
                type=LightingType.RIM,
                intensity=0.8,
                temperature=5600,
                direction_deg=135,
                softness=0.3
            ),
            LightingParams(
                type=LightingType.BACK,
                intensity=0.3,
                temperature=6000,
                direction_deg=180,
                softness=0.1
            )
        ]
    
    @classmethod
    def get_preset(cls, name: str) -> List[LightingParams]:
        presets = {
            "film_noir": cls.film_noir,
            "golden_hour": cls.golden_hour,
            "studio_portrait": cls.studio_portrait,
            "horror": cls.horror,
            "sci_fi": cls.sci_fi,
        }
        return presets.get(name, cls.studio_portrait)()
    
    @staticmethod
    def horror() -> List[LightingParams]:
        return [
            LightingParams(
                type=LightingType.KEY,
                intensity=0.6,
                temperature=4200,
                direction_deg=90,
                softness=0.2
            ),
            LightingParams(
                type=LightingType.PRACTICAL,
                intensity=0.3,
                temperature=1800,
                direction_deg=0,
                softness=0.9
            )
        ]
    
    @staticmethod
    def sci_fi() -> List[LightingParams]:
        return [
            LightingParams(
                type=LightingType.KEY,
                intensity=0.9,
                temperature=8000,
                direction_deg=60,
                softness=0.4
            ),
            LightingParams(
                type=LightingType.FILL,
                intensity=0.3,
                temperature=10000,
                direction_deg=300,
                softness=0.6
            ),
            LightingParams(
                type=LightingType.PRACTICAL,
                intensity=0.5,
                temperature=4000,
                direction_deg=0,
                softness=0.1
            )
        ]