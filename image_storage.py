"""
HELIX IMAGE STORAGE SYSTEM
Stores images inside each website's folder
Easy upload of custom images + AI generated
"""

import os
import json
import requests
import hashlib
import shutil
from datetime import datetime
from pathlib import Path


class ImageStorage:
    def __init__(self):
        """
        Images live inside each website folder
        """
        self.helix_root = Path(__file__).parent.parent

        # Website folders and their image directories
        self.websites = {
            "longevity_futures": {
                "path": self.helix_root / "longevityfutures" / "images",
                "catalog": self.helix_root / "longevityfutures" / "image_catalog.json",
                "category": "health"
            },
            "silent_ai": {
                "path": self.helix_root / "silent-ai" / "images",
                "catalog": self.helix_root / "silent-ai" / "image_catalog.json",
                "category": "tech"
            },
            "ask_market": {
                "path": self.helix_root / "askmarket" / "images",
                "catalog": self.helix_root / "askmarket" / "image_catalog.json",
                "category": "shopping"
            },
            "event_followers": {
                "path": self.helix_root / "eventfollowers" / "images",
                "catalog": self.helix_root / "eventfollowers" / "image_catalog.json",
                "category": "events"
            },
            "inspector_deepdive": {
                "path": self.helix_root / "inspectordeepdive" / "images",
                "catalog": self.helix_root / "inspectordeepdive" / "image_catalog.json",
                "category": "education"
            },
            "empire_enthusiast": {
                "path": self.helix_root / "empureenthusiast" / "images",
                "catalog": self.helix_root / "empureenthusiast" / "image_catalog.json",
                "category": "history"
            },
            "dream_wizz": {
                "path": self.helix_root / "dreamwizz" / "images",
                "catalog": self.helix_root / "dreamwizz" / "image_catalog.json",
                "category": "entertainment"
            },
            "urban_green_mowing": {
                "path": self.helix_root / "urbangreenmowing" / "images",
                "catalog": self.helix_root / "urbangreenmowing" / "image_catalog.json",
                "category": "services"
            }
        }

        # Create image folders
        for site, info in self.websites.items():
            info["path"].mkdir(parents=True, exist_ok=True)
            # Create subfolders for organization
            (info["path"] / "ai_generated").mkdir(exist_ok=True)
            (info["path"] / "uploaded").mkdir(exist_ok=True)
            (info["path"] / "used").mkdir(exist_ok=True)

    def _load_catalog(self, site: str) -> dict:
        """Load catalog for a website"""
        catalog_path = self.websites[site]["catalog"]
        if catalog_path.exists():
            with open(catalog_path, 'r') as f:
                return json.load(f)
        return {"images": [], "total": 0}

    def _save_catalog(self, site: str, catalog: dict):
        """Save catalog for a website"""
        catalog_path = self.websites[site]["catalog"]
        with open(catalog_path, 'w') as f:
            json.dump(catalog, f, indent=2)

    def save_from_url(self, site: str, image_url: str, prompt: str, tags: list = None) -> dict:
        """
        Download AI-generated image and save to website folder

        Args:
            site: Website key (e.g., 'longevity_futures')
            image_url: URL from DALL-E
            prompt: The prompt used
            tags: Searchable tags

        Returns:
            dict with local path and catalog entry
        """
        if site not in self.websites:
            return {"success": False, "error": f"Unknown site: {site}"}

        tags = tags or []
        site_info = self.websites[site]

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:6]
        clean_name = "_".join(prompt.split()[:3]).lower()
        clean_name = "".join(c for c in clean_name if c.isalnum() or c == "_")[:20]
        filename = f"{timestamp}_{clean_name}_{prompt_hash}.png"

        file_path = site_info["path"] / "ai_generated" / filename

        try:
            # Download
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                f.write(response.content)

            # Add to catalog
            catalog = self._load_catalog(site)
            entry = {
                "id": catalog["total"] + 1,
                "filename": filename,
                "path": str(file_path),
                "folder": "ai_generated",
                "prompt": prompt,
                "tags": tags,
                "source": "dall-e",
                "created": datetime.now().isoformat(),
                "used": False,
                "used_on": []
            }
            catalog["images"].append(entry)
            catalog["total"] += 1
            self._save_catalog(site, catalog)

            print(f"[STORAGE] Saved: {site}/ai_generated/{filename}")

            return {
                "success": True,
                "image_id": entry["id"],
                "path": str(file_path),
                "filename": filename,
                "site": site
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_image(self, site: str, source_path: str, description: str, tags: list = None) -> dict:
        """
        Upload/copy an image you found or made

        Args:
            site: Website key
            source_path: Path to the image file (can be anywhere on your PC)
            description: What the image is about
            tags: Searchable tags

        Returns:
            dict with result
        """
        if site not in self.websites:
            return {"success": False, "error": f"Unknown site: {site}"}

        source = Path(source_path)
        if not source.exists():
            return {"success": False, "error": f"File not found: {source_path}"}

        tags = tags or []
        site_info = self.websites[site]

        # Generate new filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_name = "_".join(description.split()[:3]).lower()
        clean_name = "".join(c for c in clean_name if c.isalnum() or c == "_")[:20]
        ext = source.suffix or ".png"
        filename = f"{timestamp}_{clean_name}{ext}"

        dest_path = site_info["path"] / "uploaded" / filename

        try:
            # Copy file
            shutil.copy2(source, dest_path)

            # Add to catalog
            catalog = self._load_catalog(site)
            entry = {
                "id": catalog["total"] + 1,
                "filename": filename,
                "path": str(dest_path),
                "folder": "uploaded",
                "prompt": description,
                "tags": tags,
                "source": "uploaded",
                "original_path": str(source),
                "created": datetime.now().isoformat(),
                "used": False,
                "used_on": []
            }
            catalog["images"].append(entry)
            catalog["total"] += 1
            self._save_catalog(site, catalog)

            print(f"[STORAGE] Uploaded: {site}/uploaded/{filename}")

            return {
                "success": True,
                "image_id": entry["id"],
                "path": str(dest_path),
                "filename": filename,
                "site": site
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def bulk_upload(self, site: str, folder_path: str, default_tags: list = None) -> dict:
        """
        Upload all images from a folder

        Args:
            site: Website key
            folder_path: Folder containing images
            default_tags: Tags to apply to all

        Returns:
            dict with results
        """
        folder = Path(folder_path)
        if not folder.exists():
            return {"success": False, "error": f"Folder not found: {folder_path}"}

        results = []
        extensions = ['.png', '.jpg', '.jpeg', '.gif', '.webp']

        for file in folder.iterdir():
            if file.suffix.lower() in extensions:
                result = self.upload_image(
                    site,
                    str(file),
                    file.stem.replace("_", " ").replace("-", " "),
                    default_tags
                )
                results.append(result)

        success_count = sum(1 for r in results if r.get("success"))

        return {
            "success": True,
            "uploaded": success_count,
            "failed": len(results) - success_count,
            "results": results
        }

    def get_unused(self, site: str, limit: int = 10) -> list:
        """Get images that haven't been used yet"""
        if site not in self.websites:
            return []

        catalog = self._load_catalog(site)
        unused = [img for img in catalog["images"] if not img["used"]]
        return unused[:limit]

    def get_by_tags(self, site: str, tags: list, limit: int = 10) -> list:
        """Find images by tags"""
        if site not in self.websites:
            return []

        catalog = self._load_catalog(site)
        results = []

        for img in catalog["images"]:
            img_tags = [t.lower() for t in img.get("tags", [])]
            if any(t.lower() in img_tags for t in tags):
                results.append(img)
                if len(results) >= limit:
                    break

        return results

    def mark_used(self, site: str, image_id: int, platform: str = "facebook"):
        """Mark image as used"""
        if site not in self.websites:
            return

        catalog = self._load_catalog(site)
        for img in catalog["images"]:
            if img["id"] == image_id:
                img["used"] = True
                img["used_on"].append({
                    "platform": platform,
                    "date": datetime.now().isoformat()
                })
                break
        self._save_catalog(site, catalog)

    def get_random_unused(self, site: str) -> dict:
        """Get a random unused image"""
        import random
        unused = self.get_unused(site, limit=100)
        if unused:
            return random.choice(unused)
        return None

    def list_all(self, site: str) -> list:
        """List all images for a site"""
        if site not in self.websites:
            return []
        catalog = self._load_catalog(site)
        return catalog["images"]

    def get_stats(self) -> dict:
        """Get stats for all websites"""
        stats = {}
        for site in self.websites:
            catalog = self._load_catalog(site)
            used = sum(1 for img in catalog["images"] if img["used"])
            stats[site] = {
                "total": catalog["total"],
                "used": used,
                "unused": catalog["total"] - used,
                "path": str(self.websites[site]["path"])
            }
        return stats


# Singleton
storage = ImageStorage()


# Easy functions
def save_ai_image(site: str, url: str, prompt: str, tags: list = None) -> dict:
    """Save AI generated image"""
    return storage.save_from_url(site, url, prompt, tags)

def upload(site: str, file_path: str, description: str, tags: list = None) -> dict:
    """Upload your own image"""
    return storage.upload_image(site, file_path, description, tags)

def bulk_upload(site: str, folder: str, tags: list = None) -> dict:
    """Upload folder of images"""
    return storage.bulk_upload(site, folder, tags)

def get_unused(site: str) -> list:
    """Get unused images"""
    return storage.get_unused(site)

def get_random(site: str) -> dict:
    """Get random unused image"""
    return storage.get_random_unused(site)

def find(site: str, tags: list) -> list:
    """Find by tags"""
    return storage.get_by_tags(site, tags)

def mark_used(site: str, image_id: int, platform: str = "facebook"):
    """Mark as used"""
    storage.mark_used(site, image_id, platform)

def stats() -> dict:
    """Get all stats"""
    return storage.get_stats()


if __name__ == "__main__":
    print("=== HELIX IMAGE STORAGE ===\n")
    print(json.dumps(stats(), indent=2))
