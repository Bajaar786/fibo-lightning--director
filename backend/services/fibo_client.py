"""
Professional client for FIBO API using official fal-client library
"""
import json
import time
from typing import Dict, Optional, List
import os

class FIBOClient:
    """Professional client for FIBO API using fal-client"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Set environment variable for fal-client
        os.environ["FAL_KEY"] = api_key
    
    async def generate_image(
        self,
        json_prompt: Dict,
        hdr: bool = True,
        size: str = "1024x1024",
        seed: Optional[int] = None
    ) -> Dict:
        """
        Generate image with FIBO using fal-client.subscribe()
        This is the CORRECT method - handles queue, status, and result automatically
        """
        
        start_time = time.time()
        
        try:
            import fal_client
            
            # Parse size to aspect ratio
            aspect_ratio = self._get_aspect_ratio_from_size(size)
            
            # Prepare arguments for FIBO
            arguments = {
                "structured_prompt": json_prompt,  # FIBO expects dict
                "seed": seed or int(time.time() * 1000) % 100000,
                "steps_num": 40 if hdr else 30,
                "guidance_scale": 5.0,
                "aspect_ratio": aspect_ratio,
                "negative_prompt": self._get_negative_prompt(json_prompt)
            }
            
            print(f"DEBUG: Calling FIBO with seed: {arguments['seed']}")
            
            # CORRECT: Use subscribe() - handles everything automatically
            def on_queue_update(update):
                """Optional: Track progress"""
                if hasattr(update, 'logs') and update.logs:
                    for log in update.logs:
                        if log.get('message'):
                            print(f" FIBO: {log['message']}")
            
            # This is the correct API call - NO status(), NO result() calls needed
            result = fal_client.subscribe(
                "bria/fibo/generate",  # Your model ID
                arguments=arguments,
                with_logs=True,
                on_queue_update=on_queue_update
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            print(f"DEBUG: FIBO result keys: {list(result.keys())}")
            
            # Extract image URL from result
            image_url = None
            if "image" in result and isinstance(result["image"], dict) and "url" in result["image"]:
                image_url = result["image"]["url"]
            elif "images" in result and isinstance(result["images"], list) and len(result["images"]) > 0:
                first_img = result["images"][0]
                if isinstance(first_img, dict) and "url" in first_img:
                    image_url = first_img["url"]
            elif "url" in result:
                image_url = result["url"]
            
            if not image_url:
                # For debugging
                print(f"DEBUG: Result structure: {json.dumps(result, indent=2)[:500]}...")
                raise Exception("No image URL found in FIBO response")
            
            print(f"DEBUG: Success! Image URL: {image_url[:60]}...")
            
            return {
                "success": True,
                "image_url": image_url,
                "request_id": result.get("request_id", "fibo-generated"),
                "seed": arguments["seed"],
                "processing_time_ms": processing_time,
                "size": size,
                "hdr": hdr
            }
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            print(f"ERROR: FIBO generation failed: {error_msg}")
            return {
                "success": False,
                "error": f"FIBO generation failed: {error_msg}",
                "processing_time_ms": processing_time
            }
    
    async def generate_image_async(
        self,
        json_prompt: Dict,
        hdr: bool = True,
        size: str = "1024x1024",
        seed: Optional[int] = None
    ) -> Dict:
        """
        Alternative async version using submit_async() + get()
        Use this if you need more control over the async flow
        """
        
        start_time = time.time()
        
        try:
            import fal_client
            
            # Prepare arguments
            aspect_ratio = self._get_aspect_ratio_from_size(size)
            arguments = {
                "structured_prompt": json_prompt,
                "seed": seed or int(time.time() * 1000) % 100000,
                "steps_num": 40 if hdr else 30,
                "guidance_scale": 5.0,
                "aspect_ratio": aspect_ratio,
                "negative_prompt": self._get_negative_prompt(json_prompt)
            }
            
            print(f"DEBUG: Submitting async FIBO request...")
            
            # CORRECT async pattern
            handler = await fal_client.submit_async(
                "bria/fibo/generate",
                arguments=arguments,
            )
            
            # Optional: Stream progress events
            async for event in handler.iter_events(with_logs=True):
                if hasattr(event, 'logs') and event.logs:
                    for log in event.logs:
                        print(f"Progress: {log.get('message', '')}")
            
            # Get final result
            result = await handler.get()
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Extract image URL
            if "image" in result and "url" in result["image"]:
                image_url = result["image"]["url"]
            else:
                raise Exception(f"No image URL in result. Keys: {list(result.keys())}")
            
            return {
                "success": True,
                "image_url": image_url,
                "request_id": handler.request_id,
                "processing_time_ms": processing_time,
                "size": size,
                "hdr": hdr
            }
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"FIBO async failed: {str(e)}",
                "processing_time_ms": processing_time
            }

    def _get_aspect_ratio_from_size(self, size: str) -> str:
        """Convert size string to aspect ratio"""
        size_map = {
            "1024x1024": "1:1",
            "768x768": "1:1",
            "768x1024": "3:4",
            "1024x768": "4:3",
            "1024x576": "16:9",
            "576x1024": "9:16",
            "1536x1536": "1:1",
        }
        return size_map.get(size, "1:1")

    def _get_negative_prompt(self, json_prompt: Dict) -> str:
        """Create intelligent negative prompt"""
        base_negative = "{'style_medium':'digital illustration','artistic_style':'non-realistic'}"
        
        # Add HDR-specific negatives if needed
        if json_prompt.get("style_attributes", {}).get("dynamic_range") == "hdr":
            base_negative += ", {'technical_flaws':'clipped highlights, blown out, crushed shadows'}"
        
        return base_negative
    
    def _create_fibo_json(self, user_prompt: str, lighting_params: Dict = None) -> Dict:
        """
        Create properly formatted FIBO JSON structure
        Use this to ensure your JSON matches FIBO's schema
        """
        fibo_json = {
            "short_description": user_prompt,
            "background_setting": "professional cinematic scene",
            "lighting": {
                "conditions": "studio lighting",
                "direction": "45 degrees from camera right",
                "shadows": "soft, well-defined"
            },
            "aesthetics": {
                "composition": "rule of thirds, balanced",
                "color_scheme": "cinematic, desaturated",
                "mood_atmosphere": "dramatic, intense"
            },
            "photographic_characteristics": {
                "depth_of_field": "shallow",
                "focus": "sharp on subject",
                "camera_angle": "eye level",
                "lens_focal_length": "50mm"
            },
            "style_medium": "photography",
            "artistic_style": "realistic, cinematic",
            "objects": []
        }
        
        return fibo_json
    
    async def batch_generate(
        self,
        prompts: List[Dict],
        hdr: bool = True
    ) -> List[Dict]:
        """Generate multiple images"""
        import asyncio
        
        results = []
        for i, prompt in enumerate(prompts):
            result = await self.generate_image(prompt, hdr=hdr, seed=i*1000)
            results.append(result)
            
            # Small delay to avoid rate limiting
            if i < len(prompts) - 1:
                await asyncio.sleep(1.0)
        
        return results