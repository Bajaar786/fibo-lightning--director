"""
Professional client for FIBO API with error handling and features
"""
import httpx
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
        """Generate image with FIBO using fal-client library"""
        
        start_time = time.time()
        
        try:
            # Import fal_client here to avoid import errors if not installed
            import fal_client
            
            # Parse size to aspect ratio
            aspect_ratio = self._get_aspect_ratio_from_size(size)
            
            # Prepare arguments for FIBO
            arguments = {
                "structured_prompt": json_prompt,  # FIBO expects structured_prompt as dict
                "seed": seed or int(time.time() * 1000) % 100000,
                "steps_num": 40 if hdr else 30,
                "guidance_scale": 5.0,
                "aspect_ratio": aspect_ratio,
                "negative_prompt": self._get_negative_prompt(json_prompt)
            }
            
            print(f"DEBUG: Calling FIBO with arguments: {list(arguments.keys())}")
            
            # Submit request to FIBO using correct model ID
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Submit the request
            handler = await loop.run_in_executor(
                None,
                lambda: fal_client.submit(
                    "bria/fibo/generate",  # Correct model ID from docs
                    arguments=arguments
                )
            )
            
            request_id = handler.request_id
            print(f"DEBUG: Submitted FIBO request with ID: {request_id}")
            
            # Poll for completion
            max_wait_time = 120  # 2 minutes max
            poll_interval = 2    # Check every 2 seconds
            elapsed_time = 0
            
            while elapsed_time < max_wait_time:
                # Check status
                status = await loop.run_in_executor(
                    None,
                    lambda: fal_client.status("bria/fibo/generate", request_id, with_logs=True)
                )
                
                print(f"DEBUG: Request status: {status.get('status', 'unknown')}")
                
                if status.get("status") == "COMPLETED":
                    # Get the result
                    result = await loop.run_in_executor(
                        None,
                        lambda: fal_client.result("bria/fibo/generate", request_id)
                    )
                    break
                elif status.get("status") == "FAILED":
                    error_msg = status.get("error", "Unknown error")
                    raise Exception(f"FIBO generation failed: {error_msg}")
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                elapsed_time += poll_interval
            else:
                raise Exception(f"FIBO generation timed out after {max_wait_time} seconds")
            
            processing_time = int((time.time() - start_time) * 1000)
            
            print(f"DEBUG: FIBO result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            
            # Extract image URL from result
            image_url = None
            if isinstance(result, dict):
                if "image" in result and isinstance(result["image"], dict) and "url" in result["image"]:
                    image_url = result["image"]["url"]
                elif "images" in result and isinstance(result["images"], list) and len(result["images"]) > 0:
                    image_url = result["images"][0].get("url")
                elif "url" in result:
                    image_url = result["url"]
            
            if not image_url:
                print(f"DEBUG: Full result: {json.dumps(result, indent=2)[:1000] if isinstance(result, dict) else str(result)}")
                raise Exception("No image URL found in FIBO response")
            
            print(f"DEBUG: Successfully got image URL: {image_url[:60]}...")
            
            return {
                "success": True,
                "image_url": image_url,
                "request_id": result.get("request_id", "fibo-generated"),
                "seed": arguments["seed"],
                "processing_time_ms": processing_time,
                "size": size,
                "hdr": hdr
            }
            
        except ImportError:
            # Fallback to direct HTTP if fal-client not available
            return await self._fallback_http_generation(json_prompt, hdr, size, seed)
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            print(f"ERROR: FIBO generation failed: {error_msg}")
            return {
                "success": False,
                "error": f"FIBO generation failed: {error_msg}",
                "processing_time_ms": processing_time
            }
    
    async def _fallback_http_generation(
        self,
        json_prompt: Dict,
        hdr: bool,
        size: str,
        seed: Optional[int]
    ) -> Dict:
        """Fallback HTTP method if fal-client fails"""
        
        start_time = time.time()
        
        try:
            # Try different FIBO endpoints with correct model ID
            endpoints = [
                "https://fal.run/bria/fibo/generate",
                "https://queue.fal.run/bria/fibo/generate"
            ]
            
            payload = {
                "structured_prompt": json_prompt,
                "seed": seed or 12345,
                "steps_num": 40 if hdr else 30,
                "guidance_scale": 5.0,
                "aspect_ratio": self._get_aspect_ratio_from_size(size),
                "negative_prompt": self._get_negative_prompt(json_prompt)
            }
            
            headers = {
                "Authorization": f"Key {self.api_key}",
                "Content-Type": "application/json"
            }
            
            for endpoint in endpoints:
                try:
                    print(f"DEBUG: Trying endpoint: {endpoint}")
                    
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        response = await client.post(endpoint, json=payload, headers=headers)
                        
                        print(f"DEBUG: Response status: {response.status_code}")
                        
                        if response.status_code == 200:
                            result = response.json()
                            
                            # Extract image URL
                            image_url = None
                            if "image" in result and isinstance(result["image"], dict):
                                image_url = result["image"]["url"]
                            elif "images" in result and len(result["images"]) > 0:
                                image_url = result["images"][0]["url"]
                            
                            if image_url:
                                processing_time = int((time.time() - start_time) * 1000)
                                return {
                                    "success": True,
                                    "image_url": image_url,
                                    "request_id": result.get("request_id", "http-fallback"),
                                    "seed": payload["seed"],
                                    "processing_time_ms": processing_time,
                                    "size": size,
                                    "hdr": hdr
                                }
                        else:
                            print(f"DEBUG: Error {response.status_code}: {response.text[:200]}")
                            
                except Exception as e:
                    print(f"DEBUG: Endpoint {endpoint} failed: {str(e)}")
                    continue
            
            raise Exception("All FIBO endpoints failed")
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "error": f"HTTP fallback failed: {str(e)}",
                "processing_time_ms": processing_time
            }

    def _get_aspect_ratio_from_size(self, size: str) -> str:
        """Convert size string to aspect ratio"""
        if size == "1024x1024":
            return "1:1"
        elif size == "768x1024":
            return "3:4"
        elif size == "1024x768":
            return "4:3"
        elif size == "1024x576":
            return "16:9"
        elif size == "576x1024":
            return "9:16"
        else:
            return "1:1"  # Default square

    def _get_negative_prompt(self, json_prompt: Dict) -> str:
        """Create intelligent negative prompt based on style"""
        base_negative = "blurry, low quality, distorted, deformed, bad anatomy"
        
        # Add style-specific negatives
        if json_prompt.get("style") == "photorealistic":
            base_negative += ", cartoon, illustration, anime, painting"
        
        return base_negative
    
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