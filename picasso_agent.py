"""
PICASSO - AI Image Agent
- Fetches FREE stock images from Unsplash & Pexels
- Uses DALL-E 3 for custom AI generation (paid)
- Auto-saves to website image folders
- Bulk download capability for building image libraries
"""

from openai import OpenAI
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from image_storage import save_ai_image, get_unused, get_random, mark_used, storage
from pathlib import Path

load_dotenv()

# Free stock image API keys (free tier)
UNSPLASH_ACCESS_KEY = os.getenv('UNSPLASH_ACCESS_KEY', '')
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY', '')


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


# ===========================================
# FREE STOCK IMAGE FETCHER
# ===========================================

class FreeImageFetcher:
    """Fetch FREE stock images from Unsplash and Pexels"""

    def __init__(self):
        self.unsplash_key = UNSPLASH_ACCESS_KEY
        self.pexels_key = PEXELS_API_KEY
        self.helix_root = Path(__file__).parent.parent

    def search_unsplash(self, query: str, count: int = 10) -> list:
        """Search Unsplash for free images"""
        if not self.unsplash_key:
            print("[PICASSO] No Unsplash API key - using Pexels only")
            return []

        try:
            url = f"https://api.unsplash.com/search/photos"
            params = {
                "query": query,
                "per_page": count,
                "orientation": "landscape"
            }
            headers = {"Authorization": f"Client-ID {self.unsplash_key}"}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            for photo in data.get("results", []):
                results.append({
                    "id": photo["id"],
                    "url": photo["urls"]["regular"],  # Good quality, not too large
                    "download_url": photo["urls"]["full"],
                    "thumb": photo["urls"]["thumb"],
                    "description": photo.get("description") or photo.get("alt_description") or query,
                    "photographer": photo["user"]["name"],
                    "source": "unsplash",
                    "width": photo["width"],
                    "height": photo["height"]
                })
            return results

        except Exception as e:
            print(f"[PICASSO] Unsplash error: {e}")
            return []

    def search_pexels(self, query: str, count: int = 10) -> list:
        """Search Pexels for free images"""
        if not self.pexels_key:
            print("[PICASSO] No Pexels API key set")
            return []

        try:
            url = "https://api.pexels.com/v1/search"
            params = {
                "query": query,
                "per_page": count,
                "orientation": "landscape"
            }
            headers = {"Authorization": self.pexels_key}

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            results = []
            for photo in data.get("photos", []):
                results.append({
                    "id": str(photo["id"]),
                    "url": photo["src"]["large"],
                    "download_url": photo["src"]["original"],
                    "thumb": photo["src"]["tiny"],
                    "description": photo.get("alt") or query,
                    "photographer": photo["photographer"],
                    "source": "pexels",
                    "width": photo["width"],
                    "height": photo["height"]
                })
            return results

        except Exception as e:
            print(f"[PICASSO] Pexels error: {e}")
            return []

    def search_all(self, query: str, count: int = 20) -> list:
        """Search both Unsplash and Pexels"""
        unsplash = self.search_unsplash(query, count // 2)
        pexels = self.search_pexels(query, count // 2)

        # Interleave results
        combined = []
        for i in range(max(len(unsplash), len(pexels))):
            if i < len(unsplash):
                combined.append(unsplash[i])
            if i < len(pexels):
                combined.append(pexels[i])

        return combined[:count]

    def download_image(self, image_data: dict, site: str, tags: list = None) -> dict:
        """Download a free image and save to website folder"""
        tags = tags or []

        try:
            # Download the image
            response = requests.get(image_data["url"], timeout=30)
            response.raise_for_status()

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            source = image_data["source"]
            img_id = image_data["id"][:8]
            clean_desc = "_".join(image_data["description"].split()[:3]).lower()
            clean_desc = "".join(c for c in clean_desc if c.isalnum() or c == "_")[:20]
            filename = f"{timestamp}_{source}_{clean_desc}_{img_id}.jpg"

            # Get site path from storage
            if site not in storage.websites:
                return {"success": False, "error": f"Unknown site: {site}"}

            site_info = storage.websites[site]

            # Create stock_images subfolder
            stock_folder = site_info["path"] / "stock_images"
            stock_folder.mkdir(exist_ok=True)

            file_path = stock_folder / filename

            with open(file_path, 'wb') as f:
                f.write(response.content)

            # Add to catalog
            catalog = storage._load_catalog(site)
            entry = {
                "id": catalog["total"] + 1,
                "filename": filename,
                "path": str(file_path),
                "folder": "stock_images",
                "prompt": image_data["description"],
                "tags": tags + [image_data["source"], "stock", "free"],
                "source": image_data["source"],
                "photographer": image_data["photographer"],
                "original_id": image_data["id"],
                "created": datetime.now().isoformat(),
                "used": False,
                "used_on": []
            }
            catalog["images"].append(entry)
            catalog["total"] += 1
            storage._save_catalog(site, catalog)

            print(f"[PICASSO] Downloaded: {site}/stock_images/{filename}")

            return {
                "success": True,
                "image_id": entry["id"],
                "path": str(file_path),
                "filename": filename,
                "source": image_data["source"],
                "photographer": image_data["photographer"]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def bulk_download(self, query: str, site: str, count: int = 20, tags: list = None) -> dict:
        """
        Download multiple free images for a search query

        Args:
            query: Search term (e.g., "vitamins", "healthy woman", "sleep")
            site: Website key (e.g., "longevity_futures")
            count: Number of images to download
            tags: Additional tags to add
        """
        print(f"[PICASSO] Searching for '{query}' images...")

        images = self.search_all(query, count)

        if not images:
            return {"success": False, "error": "No images found", "downloaded": 0}

        results = []
        downloaded = 0

        for img in images:
            result = self.download_image(img, site, tags or [query])
            results.append(result)
            if result["success"]:
                downloaded += 1

        print(f"[PICASSO] Downloaded {downloaded}/{len(images)} images for '{query}'")

        return {
            "success": True,
            "query": query,
            "downloaded": downloaded,
            "failed": len(images) - downloaded,
            "results": results
        }


# Singleton instances
picasso = PicassoAgent()
free_fetcher = FreeImageFetcher()


# ===========================================
# EASY FUNCTIONS
# ===========================================

def generate_image(prompt: str, category: str = "general") -> dict:
    """Generate image using DALL-E (paid)"""
    return picasso.generate_image(prompt, category)


def generate_social_image(page_category: str, post_topic: str) -> dict:
    """Generate social media image using DALL-E (paid)"""
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


# ===========================================
# FREE IMAGE FUNCTIONS
# ===========================================

def search_free(query: str, count: int = 20) -> list:
    """Search for free stock images"""
    return free_fetcher.search_all(query, count)


def download_free(query: str, site: str = "longevity_futures", count: int = 20, tags: list = None) -> dict:
    """
    Download free stock images for a search query

    Example:
        download_free("vitamins supplements", "longevity_futures", 30)
        download_free("healthy woman wellness", "longevity_futures", 20)
        download_free("sleep bedroom peaceful", "longevity_futures", 15)
    """
    return free_fetcher.bulk_download(query, site, count, tags)


def build_image_library(site: str = "longevity_futures", queries: list = None) -> dict:
    """
    Build a comprehensive image library by downloading images for multiple queries

    Example:
        build_image_library("longevity_futures", [
            "vitamins supplements",
            "healthy woman wellness",
            "healthy man fitness",
            "sleep peaceful bedroom",
            "healthy food nutrition",
            "exercise fitness gym",
            "meditation mindfulness",
            "nature wellness outdoor"
        ])
    """
    if queries is None:
        # Default health/longevity queries
        queries = [
            "vitamins supplements health",
            "healthy woman wellness beauty",
            "healthy man fitness strength",
            "sleep peaceful rest",
            "healthy food nutrition",
            "exercise fitness active",
            "meditation mindfulness calm",
            "nature outdoor wellness",
            "skincare beauty anti-aging",
            "energy vitality lifestyle"
        ]

    total_downloaded = 0
    results = {}

    for query in queries:
        print(f"\n[PICASSO] === Downloading: {query} ===")
        result = download_free(query, site, 10)  # 10 per query
        results[query] = result
        total_downloaded += result.get("downloaded", 0)

    print(f"\n[PICASSO] === COMPLETE ===")
    print(f"[PICASSO] Total images downloaded: {total_downloaded}")

    return {
        "success": True,
        "total_downloaded": total_downloaded,
        "queries": len(queries),
        "results": results
    }


# Test
if __name__ == "__main__":
    print("=== PICASSO Image Agent ===\n")

    # Test free image search
    print("Searching for free 'vitamins' images...")
    results = search_free("vitamins health supplements", 5)

    for img in results[:3]:
        print(f"  - {img['source']}: {img['description'][:50]}...")
        print(f"    URL: {img['url'][:60]}...")

    print(f"\nFound {len(results)} free images")
    print("\nTo download images, run:")
    print("  download_free('vitamins health', 'longevity_futures', 20)")
    print("\nTo build full library:")
    print("  build_image_library('longevity_futures')")
