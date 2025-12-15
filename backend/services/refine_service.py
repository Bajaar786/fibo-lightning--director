"""
Simple but powerful refine service for FIBO JSON prompts
"""
import json
from typing import Dict, Tuple
import httpx
import os

class RefineService:
    """Modify FIBO JSON based on natural language instructions"""
    
    def __init__(self, gemini_api_key: str = None):
        self.gemini_api_key = gemini_api_key
        if gemini_api_key:
            self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_api_key}"
    
    async def refine_json(self, original_json: Dict, instruction: str) -> Tuple[Dict, Dict]:
        """
        Refine JSON based on instruction
        
        Returns: (refined_json, changes_made)
        """
        # Try Gemini first if available
        if self.gemini_api_key:
            try:
                return await self._refine_with_gemini(original_json, instruction)
            except:
                pass
        
        # Fallback: Rule-based refinement
        return self._refine_with_rules(original_json, instruction)
    
    async def _refine_with_gemini(self, original_json: Dict, instruction: str) -> Tuple[Dict, Dict]:
        """Use Gemini to intelligently modify JSON"""
        
        prompt = f"""
        You are a cinematography expert modifying a FIBO AI generation prompt.
        
        CURRENT JSON PROMPT:
        {json.dumps(original_json, indent=2)}
        
        INSTRUCTION: "{instruction}"
        
        Modify ONLY the parts of the JSON that need to change based on the instruction.
        Keep everything else exactly the same.
        
        Return TWO JSON objects in this exact format:
        
        {{
            "refined_json": {{...complete modified JSON...}},
            "changes": {{"lighting": "made darker", "mood": "more dramatic"}}
        }}
        
        The "changes" object should briefly describe what you changed.
        """
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.gemini_url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}]
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                # Extract JSON from response
                text = text.strip()
                if "```json" in text:
                    json_text = text.split("```json")[1].split("```")[0].strip()
                else:
                    # Try to find JSON object
                    start = text.find('{')
                    end = text.rfind('}') + 1
                    json_text = text[start:end]
                
                result_data = json.loads(json_text)
                return result_data["refined_json"], result_data.get("changes", {})
        
        raise Exception("Gemini refinement failed")
    
    def _refine_with_rules(self, original_json: Dict, instruction: str) -> Tuple[Dict, Dict]:
        """Rule-based refinement (fallback)"""
        
        instruction_lower = instruction.lower()
        refined_json = json.loads(json.dumps(original_json))  # Deep copy
        changes = {}
        
        # Lighting adjustments
        if any(word in instruction_lower for word in ["darker", "dim", "low light"]):
            self._adjust_lighting(refined_json, "intensity", 0.7)
            changes["lighting"] = "reduced intensity by 30%"
        
        if any(word in instruction_lower for word in ["brighter", "more light", "increase light"]):
            self._adjust_lighting(refined_json, "intensity", 1.3)
            changes["lighting"] = "increased intensity by 30%"
        
        if any(word in instruction_lower for word in ["warmer", "orange", "golden"]):
            self._adjust_lighting(refined_json, "temperature", -1500)  # Lower temp = warmer
            changes["color"] = "made warmer (lower color temperature)"
        
        if any(word in instruction_lower for word in ["cooler", "blue", "colder"]):
            self._adjust_lighting(refined_json, "temperature", 1500)  # Higher temp = cooler
            changes["color"] = "made cooler (higher color temperature)"
        
        # Time of day
        if "night" in instruction_lower or "evening" in instruction_lower:
            refined_json = self._apply_night_transformation(refined_json)
            changes["time"] = "changed to night"
        
        if any(word in instruction_lower for word in ["day", "daytime", "sunny"]):
            refined_json = self._apply_day_transformation(refined_json)
            changes["time"] = "changed to daytime"
        
        # Weather
        if "rain" in instruction_lower:
            self._add_weather(refined_json, "rain")
            changes["weather"] = "added rain"
        
        if any(word in instruction_lower for word in ["fog", "misty", "hazy"]):
            self._add_weather(refined_json, "fog")
            changes["weather"] = "added fog/mist"
        
        # Camera adjustments
        if any(word in instruction_lower for word in ["wide angle", "wide shot", "establishing"]):
            self._adjust_camera(refined_json, "lens", "24mm")
            changes["camera"] = "changed to wide angle lens"
        
        if any(word in instruction_lower for word in ["close up", "tight shot", "portrait"]):
            self._adjust_camera(refined_json, "lens", "85mm")
            changes["camera"] = "changed to portrait lens"
        
        # Mood/atmosphere
        if any(word in instruction_lower for word in ["moody", "dramatic", "noir"]):
            self._adjust_mood(refined_json, "dramatic")
            changes["mood"] = "made more dramatic/moody"
        
        if any(word in instruction_lower for word in ["happy", "bright", "cheerful"]):
            self._adjust_mood(refined_json, "bright")
            changes["mood"] = "made brighter/cheerful"
        
        # If no specific rules matched, try generic adjustment
        if not changes:
            changes["general"] = "applied creative adjustment based on instruction"
        
        return refined_json, changes
    
    def _adjust_lighting(self, json_data: Dict, attribute: str, factor: float):
        """Adjust lighting parameters"""
        if "lighting" not in json_data:
            json_data["lighting"] = {}
        
        if attribute == "intensity":
            current = json_data["lighting"].get("intensity", 1.0)
            json_data["lighting"]["intensity"] = max(0.1, min(current * factor, 2.0))
        elif attribute == "temperature":
            current = json_data["lighting"].get("temperature", 5600)
            json_data["lighting"]["temperature"] = max(1000, min(current + factor, 10000))
    
    def _apply_night_transformation(self, json_data: Dict) -> Dict:
        """Transform scene to night"""
        if "environment" in json_data:
            json_data["environment"] = f"night time, {json_data['environment']}"
        
        if "lighting" not in json_data:
            json_data["lighting"] = {}
        
        json_data["lighting"]["time_of_day"] = "night"
        json_data["lighting"]["moonlight"] = True
        json_data["lighting"]["intensity"] = 0.5
        
        if "color_palette" not in json_data:
            json_data["color_palette"] = []
        json_data["color_palette"].extend(["dark blue", "deep shadows", "moonlit"])
        
        return json_data
    
    def _apply_day_transformation(self, json_data: Dict) -> Dict:
        """Transform scene to daytime"""
        if "environment" in json_data:
            json_data["environment"] = f"daytime, sunny, {json_data['environment']}"
        
        if "lighting" not in json_data:
            json_data["lighting"] = {}
        
        json_data["lighting"]["time_of_day"] = "day"
        json_data["lighting"]["sunlight"] = True
        json_data["lighting"]["intensity"] = 1.2
        
        return json_data
    
    def _add_weather(self, json_data: Dict, weather_type: str):
        """Add weather effects"""
        if "environment" not in json_data:
            json_data["environment"] = ""
        
        json_data["environment"] = f"{weather_type}y, {json_data['environment']}"
        
        if "atmosphere" not in json_data:
            json_data["atmosphere"] = {}
        json_data["atmosphere"]["weather"] = weather_type
    
    def _adjust_camera(self, json_data: Dict, setting: str, value: str):
        """Adjust camera settings"""
        if "camera" not in json_data:
            json_data["camera"] = {}
        json_data["camera"][setting] = value
    
    def _adjust_mood(self, json_data: Dict, mood: str):
        """Adjust scene mood"""
        if "lighting" not in json_data:
            json_data["lighting"] = {}
        
        json_data["lighting"]["mood"] = mood
        
        if mood == "dramatic":
            json_data["lighting"]["contrast"] = "high"
            json_data["lighting"]["shadows"] = "deep"
        elif mood == "bright":
            json_data["lighting"]["contrast"] = "medium"
            json_data["lighting"]["shadows"] = "soft"