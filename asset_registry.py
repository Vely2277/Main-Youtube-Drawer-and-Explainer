"""Asset registry with metadata for validation and intelligent selection."""

from pathlib import Path
from typing import Any


class AssetRegistry:
    """Registry of available SVG assets with metadata."""

    def __init__(self, asset_dir: Path):
        self.asset_dir = asset_dir
        self.assets: dict[str, dict[str, Any]] = {}
        self._scan_assets()

    def _scan_assets(self) -> None:
        """Scan asset directory and build registry."""
        if not self.asset_dir.exists():
            return

        for svg_file in self.asset_dir.rglob("*.svg"):
            relative_path = svg_file.relative_to(self.asset_dir)
            asset_key = str(relative_path).replace("\\", "/")

            # Extract metadata from filename
            metadata = self._extract_metadata(asset_key, svg_file)
            self.assets[asset_key] = metadata

    def _extract_metadata(self, asset_key: str, svg_path: Path) -> dict[str, Any]:
        """Extract metadata from asset path and filename."""
        parts = asset_key.split("/")
        filename = parts[-1].replace(".svg", "")

        # Determine role from path
        role = self._infer_role(asset_key)

        # Determine zone from role
        zone = self._infer_zone(role)

        # Determine default scale from role
        default_scale = self._infer_scale(role)

        # Extract tags from filename
        tags = self._extract_tags(filename)

        return {
            "path": asset_key,
            "filename": filename,
            "role": role,
            "zone": zone,
            "default_scale": default_scale,
            "tags": tags,
            "category": parts[0] if len(parts) > 1 else "unknown",
        }

    def _infer_role(self, asset_key: str) -> str:
        """Infer role from asset path."""
        key_lower = asset_key.lower()

        if "open_peeps" in key_lower or "person" in key_lower or "character" in key_lower:
            return "character"
        elif "building" in key_lower or "structure" in key_lower or "house" in key_lower:
            return "structure"
        elif "cloud" in key_lower or "sun" in key_lower or "sky" in key_lower:
            return "sky_entity"
        elif "background" in key_lower:
            return "background"
        elif "foreground" in key_lower:
            return "foreground"
        else:
            return "prop"

    def _infer_zone(self, role: str) -> str:
        """Infer zone from role."""
        zone_map = {
            "character": "ground",
            "prop": "ground",
            "structure": "ground",
            "sky_entity": "sky",
            "background": "background",
            "foreground": "foreground",
        }
        return zone_map.get(role, "ground")

    def _infer_scale(self, role: str) -> float:
        """Infer default scale from role."""
        scale_map = {
            "character": 0.25,
            "prop": 0.10,
            "structure": 0.40,
            "sky_entity": 0.15,
            "background": 0.50,
            "foreground": 0.30,
        }
        return scale_map.get(role, 0.15)

    def _extract_tags(self, filename: str) -> list[str]:
        """Extract tags from filename."""
        # Split by common separators
        tags = filename.replace("-", " ").replace("_", " ").split()
        return [tag.lower() for tag in tags if tag]

    def asset_exists(self, asset_path: str) -> bool:
        """Check if asset exists in registry."""
        return asset_path in self.assets

    def get_asset(self, asset_path: str) -> dict[str, Any] | None:
        """Get asset metadata by path."""
        return self.assets.get(asset_path)

    def find_assets_by_role(self, role: str) -> list[str]:
        """Find all assets with a specific role."""
        return [path for path, meta in self.assets.items() if meta["role"] == role]

    def find_assets_by_tag(self, tag: str) -> list[str]:
        """Find all assets with a specific tag."""
        tag_lower = tag.lower()
        return [
            path
            for path, meta in self.assets.items()
            if tag_lower in meta["tags"]
        ]

    def find_assets_by_category(self, category: str) -> list[str]:
        """Find all assets in a specific category."""
        return [
            path
            for path, meta in self.assets.items()
            if meta["category"] == category
        ]

    def get_default_asset_for_role(self, role: str) -> str | None:
        """Get a default asset for a specific role."""
        assets = self.find_assets_by_role(role)
        return assets[0] if assets else None

    def validate_asset_path(self, asset_path: str) -> tuple[bool, str]:
        """Validate asset path and return (is_valid, error_message)."""
        if not asset_path:
            return False, "Asset path is empty"

        if not asset_path.endswith(".svg"):
            return False, "Asset path must end with .svg"

        if ".." in asset_path or asset_path.startswith("/") or asset_path.startswith("\\"):
            return False, "Asset path cannot contain '..' or start with '/' or '\\'"

        if not self.asset_exists(asset_path):
            return False, f"Asset not found: {asset_path}"

        return True, ""

    def get_asset_suggestions(self, asset_path: str, max_suggestions: int = 5) -> list[str]:
        """Get similar asset suggestions for a non-existent path."""
        if self.asset_exists(asset_path):
            return []

        # Extract filename without extension
        filename = Path(asset_path).stem.lower()

        # Find assets with similar names
        suggestions = []
        for path, meta in self.assets.items():
            if filename in meta["filename"].lower() or meta["filename"].lower() in filename:
                suggestions.append(path)
                if len(suggestions) >= max_suggestions:
                    break

        return suggestions

    def get_all_assets(self) -> dict[str, dict[str, Any]]:
        """Get all assets in registry."""
        return self.assets.copy()

    def get_assets_by_zone(self, zone: str) -> list[str]:
        """Get all assets for a specific zone."""
        return [path for path, meta in self.assets.items() if meta["zone"] == zone]

    def get_assets_by_category(self, category: str) -> list[str]:
        """Get all assets in a specific category."""
        return self.find_assets_by_category(category)
