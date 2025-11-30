"""
PICASSO - AI Image Generation Agent
Uses DALL-E 3 to generate images for social media posts
Auto-saves to website image folders
"""

from openai import OpenAI
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from image_storage import save_ai_image, get_unused, get_random, mark_used

load_dotenv()


class PicassoAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.generated_images = []  # Store generated images

        # Map category to website storage key
        self.category_to_site = {
            "health": "longevity_futures",
            "tech": "silent_ai",
            "shopping": "ask_market",
            "events": "event_followers",
            "education": "inspector_deepdive",
            "history": "empire_enthusiast",
            "entertainment": "dream_wizz",
            "services": "urban_green_mowing",
            "general": "longevity_futures"  # Default
        }

        # Style presets for different page categories
        self.style_presets = {
            "health": "Clean, professional, wellness-focused. Bright colors, nature elements, healthy lifestyle imagery.",
            "tech": "Modern, futuristic, digital aesthetic. Blue tones, circuit patterns, AI/robot elements.",
            "shopping": "Vibrant, eye-catching, product-focused. Bold colors, clean backgrounds, commercial appeal.",
            "events": "Exciting, dynamic, social atmosphere. Event lighting, crowds, celebration vibes.",
            "education": "Academic, thoughtful, knowledge-focused. Books, libraries, learning environments.",
            "history": "Classical, vintage, historical aesthetic. Sepia tones, ancient architecture, historical imagery.",
            "entertainment": "Fun, colorful, creative. Fantasy elements, imagination, whimsical.",
            "services": "Professional, trustworthy, local business. Green/nature elements for lawn care."
        }

    def generate_image(self, prompt: str, category: str = "general", size: str = "1024x1024") -> dict:
        """
        Generate an image using DALL-E 3

        Args:
            prompt: Description of the image to generate
            category: Category for style preset (health, tech, events, etc.)
            size: Image size (1024x1024, 1792x1024, 1024x1792)

        Returns:
            dict with image_url, revised_prompt, and metadata
        """
        try:
            # Enhance prompt with style preset
            style = self.style_presets.get(category, "Professional, high-quality, social media optimized.")
            enhanced_prompt = f"{prompt}. Style: {style} No text or words in the image."

            response = self.client.images.generate(
                model="dall-e-3",
                prompt=enhanced_prompt,
                size=size,
                quality="standard",
                n=1
            )

            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt

            # Save to website's image folder
            site_key = self.category_to_site.get(category, "longevity_futures")
            storage_result = save_ai_image(
                site=site_key,
                url=image_url,
                prompt=revised_prompt,
                tags=prompt.split()[:5]  # First 5 words as tags
            )

            # Store the generated image
            image_record = {
                "id": len(self.generated_images) + 1,
                "original_prompt": prompt,
                "enhanced_prompt": enhanced_prompt,
                "revised_prompt": revised_prompt,
                "image_url": image_url,
                "local_path": storage_result.get("path") if storage_result.get("success") else None,
                "storage_id": storage_result.get("image_id") if storage_result.get("success") else None,
                "category": category,
                "size": size,
                "created_at": datetime.now().isoformat(),
                "status": "generated"
            }
            self.generated_images.append(image_record)

            return {
                "success": True,
                "image_url": image_url,
                "local_path": storage_result.get("path"),
                "revised_prompt": revised_prompt,
                "image_id": image_record["id"],
                "storage_id": storage_result.get("image_id")
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_social_image(self, page_category: str, post_topic: str) -> dict:
        """
        Generate an image optimized for social media posting

        Args:
            page_category: The category of the Facebook page (health, tech, etc.)
            post_topic: What the post is about

        Returns:
            dict with image URL ready for Facebook posting
        """
        # Create a social-media-optimized prompt
        prompt = f"Create a visually striking social media image for a post about: {post_topic}. The image should be eye-catching, professional, and suitable for Facebook. No text or watermarks."

        # Use 1:1 aspect ratio for Facebook posts
        result = self.generate_image(prompt, page_category, "1024x1024")

        return result

    def get_gallery(self) -> list:
        """Get all generated images"""
        return self.generated_images

    def get_pending_approval(self) -> list:
        """Get images pending approval"""
        return [img for img in self.generated_images if img["status"] == "generated"]

    def approve_image(self, image_id: int) -> dict:
        """Approve an image for use"""
        for img in self.generated_images:
            if img["id"] == image_id:
                img["status"] = "approved"
                return {"success": True, "message": f"Image {image_id} approved"}
        return {"success": False, "error": "Image not found"}

    def reject_image(self, image_id: int) -> dict:
        """Reject an image"""
        for img in self.generated_images:
            if img["id"] == image_id:
                img["status"] = "rejected"
                return {"success": True, "message": f"Image {image_id} rejected"}
        return {"success": False, "error": "Image not found"}


# Singleton instance
picasso = PicassoAgent()


def generate_image(prompt: str, category: str = "general") -> dict:
    """Generate image using PICASSO"""
    return picasso.generate_image(prompt, category)


def generate_social_image(page_category: str, post_topic: str) -> dict:
    """Generate social media image"""
    return picasso.generate_social_image(page_category, post_topic)


def get_gallery() -> list:
    """Get all generated images"""
    return picasso.get_gallery()


def get_pending() -> list:
    """Get pending images"""
    return picasso.get_pending_approval()


def approve(image_id: int) -> dict:
    """Approve image"""
    return picasso.approve_image(image_id)


def reject(image_id: int) -> dict:
    """Reject image"""
    return picasso.reject_image(image_id)


# Test
if __name__ == "__main__":
    print("Testing PICASSO Image Generation...")
    result = generate_social_image("health", "The benefits of intermittent fasting for longevity")
    print(json.dumps(result, indent=2))
