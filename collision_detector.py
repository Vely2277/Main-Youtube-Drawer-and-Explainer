"""Collision detection system for scene entities."""

from dataclasses import dataclass
from typing import Any


@dataclass
class BoundingBox:
    """Axis-aligned bounding box."""
    x: float
    y: float
    width: float
    height: float

    def overlaps(self, other: "BoundingBox") -> bool:
        """Check if this box overlaps with another."""
        return not (
            self.x + self.width < other.x
            or other.x + other.width < self.x
            or self.y + self.height < other.y
            or other.y + other.height < self.y
        )

    def intersection_area(self, other: "BoundingBox") -> float:
        """Calculate intersection area with another box."""
        x_overlap = max(0, min(self.x + self.width, other.x + other.width) - max(self.x, other.x))
        y_overlap = max(0, min(self.y + self.height, other.y + other.height) - max(self.y, other.y))
        return x_overlap * y_overlap

    def union_area(self, other: "BoundingBox") -> float:
        """Calculate union area with another box."""
        intersection = self.intersection_area(other)
        return self.area() + other.area() - intersection

    def area(self) -> float:
        """Calculate area of bounding box."""
        return self.width * self.height

    def iou(self, other: "BoundingBox") -> float:
        """Calculate Intersection over Union."""
        intersection = self.intersection_area(other)
        union = self.union_area(other)
        return intersection / union if union > 0 else 0.0


class CollisionDetector:
    """Detect collisions between scene entities."""

    def __init__(self, iou_threshold: float = 0.1):
        self.iou_threshold = iou_threshold

    def detect_collisions(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect collisions between entities."""
        collisions = []

        # Create bounding boxes for all entities
        boxes = []
        for i, entity in enumerate(entities):
            box = self._create_bounding_box(entity, i)
            if box:
                boxes.append((i, box))

        # Check all pairs for collisions
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                idx1, box1 = boxes[i]
                idx2, box2 = boxes[j]

                # Skip if same motion group (they move together)
                entity1 = entities[idx1]
                entity2 = entities[idx2]
                if entity1.get("motion_group") and entity1.get("motion_group") == entity2.get("motion_group"):
                    continue

                # Check for overlap
                if box1.overlaps(box2):
                    iou = box1.iou(box2)
                    if iou > self.iou_threshold:
                        collisions.append({
                            "entity1_index": idx1,
                            "entity2_index": idx2,
                            "entity1_asset": entity1.get("asset", "unknown"),
                            "entity2_asset": entity2.get("asset", "unknown"),
                            "iou": iou,
                            "intersection_area": box1.intersection_area(box2),
                        })

        return collisions

    def _create_bounding_box(self, entity: dict[str, Any], index: int) -> BoundingBox | None:
        """Create bounding box for entity."""
        # This is a simplified version - in practice we'd need actual SVG dimensions
        # For now, we estimate based on scale_fraction

        scale_fraction = entity.get("scale_fraction", 0.15)
        anchor = entity.get("anchor", "center")

        # Estimate dimensions (assuming 16:9 aspect ratio for most SVGs)
        base_width = 2.0  # units
        base_height = 2.0  # units

        width = base_width * scale_fraction * 10  # Scale up for visibility
        height = base_height * scale_fraction * 10

        # Position based on anchor (simplified - actual position from solver)
        x = entity.get("x_offset", 0.0)
        y = entity.get("y_offset", 0.0)

        # Adjust for anchor
        if anchor == "bottom":
            y = y + height / 2
        elif anchor == "top":
            y = y - height / 2

        return BoundingBox(x=x, y=y, width=width, height=height)

    def resolve_collisions(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Attempt to resolve collisions by adjusting positions."""
        resolved_entities = [entity.copy() for entity in entities]
        collisions = self.detect_collisions(resolved_entities)

        for collision in collisions:
            idx1 = collision["entity1_index"]
            idx2 = collision["entity2_index"]

            # Simple resolution: move entity2 slightly
            entity2 = resolved_entities[idx2]
            current_x = entity2.get("x_offset", 0.0)
            current_y = entity2.get("y_offset", 0.0)

            # Move entity2 to the right and up
            entity2["x_offset"] = current_x + 0.5
            entity2["y_offset"] = current_y + 0.5

        return resolved_entities

    def get_collision_report(self, entities: list[dict[str, Any]]) -> dict[str, Any]:
        """Get detailed collision report."""
        collisions = self.detect_collisions(entities)

        return {
            "has_collisions": len(collisions) > 0,
            "collision_count": len(collisions),
            "collisions": collisions,
            "entity_count": len(entities),
        }


class SpatialValidator:
    """Validate spatial relationships between entities."""

    def __init__(self):
        self.collision_detector = CollisionDetector()

    def validate_spatial_relationships(self, entities: list[dict[str, Any]]) -> list[str]:
        """Validate spatial relationships between entities."""
        errors = []

        # Check for collisions
        collisions = self.collision_detector.detect_collisions(entities)
        if collisions:
            for collision in collisions:
                errors.append(
                    f"Collision between {collision['entity1_asset']} and "
                    f"{collision['entity2_asset']} (IoU: {collision['iou']:.2f})"
                )

        # Check for entities too close to frame edges
        for i, entity in enumerate(entities):
            x_offset = entity.get("x_offset", 0.0)
            y_offset = entity.get("y_offset", 0.0)
            scale = entity.get("scale_fraction", 0.15)

            # Estimate entity size
            entity_width = scale * 10
            entity_height = scale * 10

            # Check if too close to edges
            if abs(x_offset) + entity_width / 2 > 7.0:
                errors.append(f"entities[{i}]: Entity too close to horizontal frame edge")

            if abs(y_offset) + entity_height / 2 > 4.0:
                errors.append(f"entities[{i}]: Entity too close to vertical frame edge")

        return errors

    def suggest_position_adjustments(self, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Suggest position adjustments to resolve collisions."""
        suggestions = []
        collisions = self.collision_detector.detect_collisions(entities)

        for collision in collisions:
            idx1 = collision["entity1_index"]
            idx2 = collision["entity2_index"]

            entity1 = entities[idx1]
            entity2 = entities[idx2]

            # Suggest moving entity2
            suggestion = {
                "entity_index": idx2,
                "entity_asset": entity2.get("asset"),
                "current_x": entity2.get("x_offset", 0.0),
                "current_y": entity2.get("y_offset", 0.0),
                "suggested_x": entity2.get("x_offset", 0.0) + 1.0,
                "suggested_y": entity2.get("y_offset", 0.0) + 1.0,
                "reason": f"Collision with {entity1.get('asset')}",
            }
            suggestions.append(suggestion)

        return suggestions
