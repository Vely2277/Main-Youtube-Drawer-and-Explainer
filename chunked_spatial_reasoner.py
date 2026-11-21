"""Chunked LLM spatial reasoning for intelligent scene arrangement."""

import json
import re
import math
from typing import Any, List, Tuple, Dict, Optional

from ollama_client import OllamaClient


class ChunkedSpatialReasoner:
    """
    Handles chunked LLM queries for intelligent spatial reasoning.
    
    This system uses qwen2.5:0.5b to make intelligent decisions about:
    - Z-index ordering (depth perception)
    - Sky distribution (natural cloud placement, sun position)
    - Ground distribution (character positioning, structure placement)
    - Scaling adjustments (depth-based scaling, importance scaling)
    - Collision resolution (overlap detection and resolution)
    
    Each chunk is designed to be a focused, specific question that the LLM
    can answer quickly and accurately. All outputs are validated and have
    sophisticated fallback logic.
    """

    def __init__(self, ollama_client: OllamaClient):
        self.client = ollama_client
        
        # Frame constants
        self.frame_width = 14.22
        self.frame_height = 8.0
        self.ground_y = -2.35
        self.sky_y_min = 0.0
        self.sky_y_max = 4.0
        self.ground_y_min = -4.0
        self.ground_y_max = -0.5
        self.safe_margin_x = 0.5
        self.safe_margin_y = 0.5

    def pre_warm(self) -> None:
        """
        Pre-warm Ollama by sending a simple query to load the model into RAM.
        This reduces overhead for the first actual chunk query.
        """
        try:
            print("  Pre-warming Ollama model...")
            self.client.generate("hi", json_mode=False, timeout=60)
            print("  [OK] Ollama model loaded")
        except Exception as e:
            print(f"  [WARNING] Pre-warm failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")

    def chunk3_spatial_relationships(self, entities: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
        """
        Chunk 3: Determine intelligent z-index ordering based on spatial relationships.
        
        This chunk analyzes the scene to determine which entities should be in front
        or behind others, considering:
        - Natural depth relationships (clouds behind planes, people in front of buildings)
        - Category-based defaults (sky entities as background, characters as foreground)
        - Scene composition rules (rule of thirds, visual hierarchy)
        - Entity relationships (inside, on, behind, in front of)
        
        Args:
            entities: List of entity dicts with name, zone, category, relation, relation_target
            
        Returns:
            List of (entity_name, z_index) tuples, ordered by z-index ascending
        """
        # Build detailed entity context
        entity_context = []
        for e in entities:
            context = f"- {e['name']}"
            context += f" (zone: {e['zone']}, category: {e['category']})"
            if e.get('relation'):
                context += f", relation: {e['relation']}"
            if e.get('relation_target'):
                context += f" to {e['relation_target']}"
            entity_context.append(context)

        entity_list = "\n".join(entity_context)

        prompt = f"""You are an expert scene composition artist. Analyze these entities and determine their z-index ordering (depth layering).

Entities:
{entity_list}

FRAME CONTEXT:
- Frame dimensions: width {self.frame_width}, height {self.frame_height}
- Higher z-index = closer to camera (in front)
- Lower z-index = further from camera (background)

COMPOSITION RULES:
1. Sky entities (clouds, sun, moon, stars) typically have z-index 1-2 (background)
2. Ground structures (buildings, trees, mountains) typically have z-index 2-3 (mid-ground)
3. Vehicles (cars, buses, trains, planes on ground) typically have z-index 3-4
4. Props (chairs, tables, books) typically have z-index 4
5. Characters (people, passengers, pilots) typically have z-index 5-6 (foreground)

SPECIAL RELATIONSHIPS:
- If entity is "inside" another, it should have higher z-index than container
- If entity is "behind" another, it should have lower z-index
- If entity is "in front of" another, it should have higher z-index
- If entity is "on top of" another, it should have higher z-index

VISUAL HIERARCHY:
- Main subject (usually the first mentioned or largest entity) should be prominent (z-index 4-5)
- Supporting elements should be in mid-ground (z-index 2-3)
- Background elements should be subtle (z-index 1-2)

Return ONLY a JSON array like:
[["cloud_1", 1], ["building", 2], ["plane", 3], ["person", 5]]

Format: [entity_name, z_index] where z_index is an integer from 1 to 10.
Order the array by z-index ascending (background to foreground)."""

        try:
            response = self.client.generate(prompt, json_mode=True)
            result = json.loads(response)
            
            # Handle different response formats
            # LLM might return a dict with a key like "entities" containing the array
            if isinstance(result, dict):
                # Look for the array in dict values
                for key, value in result.items():
                    if isinstance(value, list):
                        result = value
                        break
            
            # Validate and normalize
            validated = []
            entity_names = [e['name'] for e in entities]
            
            for item in result:
                if isinstance(item, list) and len(item) == 2:
                    entity_name = str(item[0])
                    z_index = item[1]
                    
                    # Handle if z_index is a list (take first element)
                    if isinstance(z_index, list):
                        z_index = z_index[0] if z_index else 1
                    
                    try:
                        z_index = int(z_index)
                    except (ValueError, TypeError):
                        continue
                    
                    # Match entity name (handle suffixes like cloud_1 -> cloud)
                    matched_name = None
                    for en in entity_names:
                        # Strip suffix from LLM response
                        llm_base = entity_name.split('_')[0] if '_' in entity_name else entity_name
                        # Strip suffix from entity name
                        entity_base = en.split('_')[0] if '_' in en else en
                        if llm_base == entity_base:
                            matched_name = en
                            break
                    
                    if matched_name:
                        # Clamp to reasonable range
                        z_index = max(1, min(10, z_index))
                        validated.append((matched_name, z_index))
            
            # Sort by z-index
            validated.sort(key=lambda x: x[1])
            
            return validated
            
        except Exception as e:
            print(f"  [ERROR] Chunk 3 failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")
            return self._fallback_z_index(entities)

    def chunk4_sky_distribution(self, entities: List[Dict[str, Any]]) -> List[Tuple[str, float, float]]:
        """
        Chunk 4: Calculate intelligent coordinates for sky entities.
        
        This chunk places sky entities (clouds, sun, moon, stars, planes, birds)
        in the sky zone with natural, aesthetically pleasing distribution.
        
        Considerations:
        - Natural cloud patterns (not straight lines, organic variation)
        - Sun/moon position (typically higher, often off-center for composition)
        - Plane/bird positioning (varied heights, dynamic angles)
        - Depth perception (higher entities = further away = smaller scale handled later)
        - Rule of thirds (place key elements at 1/3 or 2/3 positions)
        - Avoiding overlaps (clouds shouldn't cover sun unless intentional)
        - Visual balance (even distribution across frame)
        
        Args:
            entities: List of sky entity dicts
            
        Returns:
            List of (entity_name, x, y) tuples with coordinates
        """
        sky_entities = [e for e in entities if e['zone'] == 'sky']
        if not sky_entities:
            return []

        # Build detailed entity context
        entity_context = []
        for e in sky_entities:
            context = f"- {e['name']} (category: {e['category']}, scale: {e.get('scale', 0.1)})"
            entity_context.append(context)

        entity_list = "\n".join(entity_context)

        prompt = f"""You are an expert sky scene artist. Place these sky entities naturally and aesthetically.

Entities:
{entity_list}

FRAME CONTEXT:
- Frame dimensions: width {self.frame_width}, height {self.frame_height}
- Sky zone: y between {self.sky_y_min} and {self.sky_y_max}
- X range: -{self.frame_width/2} to {self.frame_width/2}
- Ground line: y = {self.ground_y}

COMPOSITION PRINCIPLES:
1. Rule of Thirds: Place important elements at x = ±4.7, y = ±2.6 for visual interest
2. Natural Cloud Distribution: Vary heights (y) and spacing (x) - avoid straight lines
3. Sun/Moon Position: Typically higher (y > 2.5), often slightly off-center
4. Depth Perception: Higher y = further away, lower y = closer
5. Visual Balance: Distribute entities evenly across the frame width
6. Avoid Overlaps: Don't place clouds directly over sun/moon unless for effect

SPECIFIC GUIDELINES:
- Sun/moon: Place at y > 2.5, x between -5 and 5 (off-center preferred)
- Clouds: Vary y between 1.0 and 3.5, spread x across -6 to 6
- Plane/bird: Can be at various heights, typically y between 1.5 and 3.0
- Stars: Small, scattered, typically y > 2.0

ORGANIC VARIATION:
- Don't place entities in a straight line
- Vary heights by at least 0.3 units between adjacent entities
- Use natural spacing (not perfectly even)
- Consider visual flow (left to right reading direction)

Return ONLY a JSON array like:
[["cloud_1", -4.5, 2.8], ["sun", 5.0, 3.2], ["plane", 0.0, 2.0]]

Format: [entity_name, x, y] where x and y are floats."""

        try:
            response = self.client.generate(prompt, json_mode=True)
            result = json.loads(response)
            
            # Handle different response formats
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, list):
                        result = value
                        break
            
            # Validate and clamp
            validated = []
            for item in result:
                if isinstance(item, list) and len(item) == 3:
                    entity_name = str(item[0])
                    x = float(item[1])
                    y = float(item[2])
                    # Clamp to bounds
                    x = max(-self.frame_width/2 + self.safe_margin_x, 
                           min(self.frame_width/2 - self.safe_margin_x, x))
                    y = max(self.sky_y_min + self.safe_margin_y, 
                           min(self.sky_y_max - self.safe_margin_y, y))
                    validated.append((entity_name, x, y))
            
            return validated
            
        except Exception as e:
            print(f"  [ERROR] Chunk 4 failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")
            return self._fallback_sky_distribution(sky_entities)

    def chunk5_ground_distribution(self, entities: List[Dict[str, Any]]) -> List[Tuple[str, float, float]]:
        """
        Chunk 5: Calculate intelligent coordinates for ground entities.
        
        This chunk places ground entities (people, buildings, trees, vehicles, props)
        on the ground with realistic positioning.
        
        Considerations:
        - Characters must stand ON the ground line (y = ground_y)
        - Structures sit on ground line with proper anchoring
        - Vehicles sit on ground with proper orientation
        - Props are placed relative to characters or structures
        - Natural spacing (people not too close, buildings with gaps)
        - Visual hierarchy (main subject centered or at rule of thirds)
        - Relationship handling (people next to buildings, cars on roads)
        - Collision avoidance (entities shouldn't overlap)
        
        Args:
            entities: List of ground entity dicts
            
        Returns:
            List of (entity_name, x, y) tuples with coordinates
        """
        ground_entities = [e for e in entities if e['zone'] == 'ground']
        if not ground_entities:
            return []

        # Build detailed entity context
        entity_context = []
        for e in ground_entities:
            context = f"- {e['name']} (category: {e['category']}, scale: {e.get('scale', 0.1)})"
            if e.get('relation'):
                context += f", relation: {e['relation']}"
            if e.get('relation_target'):
                context += f" to {e['relation_target']}"
            entity_context.append(context)

        entity_list = "\n".join(entity_context)

        prompt = f"""You are an expert ground scene artist. Place these ground entities realistically.

Entities:
{entity_list}

FRAME CONTEXT:
- Frame dimensions: width {self.frame_width}, height {self.frame_height}
- Ground line: y = {self.ground_y} (characters must stand ON this line)
- Ground zone: y between {self.ground_y_min} and {self.ground_y_max}
- X range: -{self.frame_width/2} to {self.frame_width/2}

POSITIONING RULES:
1. Characters (people, passengers, pilots): MUST be at y = {self.ground_y} (on ground line)
2. Structures (buildings, trees, houses): Sit on ground line at y = {self.ground_y}
3. Vehicles (cars, buses, trains): Sit on ground at y = {self.ground_y}
4. Props (chairs, tables, books): Can be on ground or relative to other entities

SPACING GUIDELINES:
- Characters: Space at least 1.0 unit apart (unless intentionally close)
- Buildings: Space at least 2.0 units apart
- Trees: Space at least 1.5 units apart
- Vehicles: Space at least 2.0 units apart

VISUAL COMPOSITION:
- Main subject: Place near center or at rule of thirds (x = ±4.7)
- Supporting elements: Distribute around main subject
- Background elements: Place toward edges
- Foreground elements: Place in front (lower z-index handled separately)

RELATIONSHIP HANDLING:
- If entity is "next to" another, place within 1.5 units
- If entity is "between" two others, place in the middle
- If entity is "inside" a vehicle, place at vehicle's position
- If entity is "on" something, place at that thing's position

Return ONLY a JSON array like:
[["person", 0.0, -2.35], ["building", -4.0, -2.35], ["tree", 5.0, -2.35]]

Format: [entity_name, x, y] where x and y are floats.
Characters MUST have y = {self.ground_y}."""

        try:
            response = self.client.generate(prompt, json_mode=True)
            result = json.loads(response)
            
            # Handle different response formats
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, list):
                        result = value
                        break
            
            # Validate and clamp
            validated = []
            entity_names = [e['name'] for e in entities]
            
            for item in result:
                if isinstance(item, list) and len(item) == 3:
                    entity_name = str(item[0])
                    x = float(item[1])
                    y = float(item[2])
                    
                    # Match entity name (handle suffixes)
                    matched_name = None
                    for en in entity_names:
                        llm_base = entity_name.split('_')[0] if '_' in entity_name else entity_name
                        entity_base = en.split('_')[0] if '_' in en else en
                        if llm_base == entity_base:
                            matched_name = en
                            break
                    
                    if matched_name:
                        # Clamp to bounds
                        x = max(-self.frame_width/2 + self.safe_margin_x, 
                               min(self.frame_width/2 - self.safe_margin_x, x))
                        # Force ground entities to ground line
                        if any(e['name'] == matched_name and e['zone'] == 'ground' for e in entities):
                            y = self.ground_y
                        else:
                            y = max(self.ground_y_min, min(self.ground_y_max, y))
                        validated.append((matched_name, x, y))
            
            return validated
            
        except Exception as e:
            print(f"  [ERROR] Chunk 5 failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")
            return self._fallback_ground_distribution(ground_entities)

    def chunk6_scaling_adjustments(self, entities: List[Dict[str, Any]], positions: List[Tuple[str, float, float]]) -> List[Tuple[str, float]]:
        """
        Chunk 6: Suggest intelligent scaling adjustments based on depth and importance.
        
        This chunk adjusts entity scales based on:
        - Depth perception (further entities = smaller)
        - Visual importance (main subject = larger)
        - Category norms (people vs buildings vs props)
        - Composition balance (avoid all entities being same size)
        - Relationship context (parent/child relationships)
        
        Args:
            entities: List of entity dicts
            positions: List of (entity_name, x, y) tuples
            
        Returns:
            List of (entity_name, scale) tuples
        """
        # Build detailed context
        entity_info = []
        for e in entities:
            # Find position
            pos = next((p for p in positions if p[0] == e['name']), None)
            if pos:
                x, y = pos[1], pos[2]
            else:
                x, y = 0.0, 0.0
            
            info = f"- {e['name']}"
            info += f" (current scale: {e.get('scale', 0.1)}, category: {e['category']})"
            info += f", position: x={x:.2f}, y={y:.2f}"
            if e['zone'] == 'sky':
                info += f", depth: {'far' if y > 2.5 else 'mid' if y > 1.5 else 'near'}"
            entity_info.append(info)

        entity_list = "\n".join(entity_info)

        prompt = f"""You are an expert scene artist. Review these entities and suggest scale adjustments for better composition.

Entities:
{entity_list}

SCALING PRINCIPLES:
1. Depth Perception: Higher y in sky = further away = smaller scale
2. Visual Importance: Main subject should be slightly larger
3. Category Norms:
   - Characters: 0.10-0.15 (people), 0.08-0.12 (children)
   - Buildings: 0.15-0.25 (depending on importance)
   - Trees: 0.12-0.18
   - Vehicles: 0.12-0.20
   - Sky entities: 0.08-0.15 (clouds), 0.10-0.15 (sun/moon)
4. Composition Balance: Vary scales slightly for visual interest
5. Keep Changes Small: Adjust by ±0.02 to ±0.05, not dramatic changes

DEPTH-BASED SCALING (Sky Zone):
- y > 2.5: Multiply scale by 0.8-0.9 (far away)
- y 2.0-2.5: Multiply scale by 0.9-1.0 (mid distance)
- y < 2.0: Multiply scale by 1.0-1.1 (closer)

IMPORTANCE-BASED SCALING:
- Main subject (first mentioned or central): +0.02 to +0.05
- Supporting elements: Keep current scale
- Background elements: -0.02 to -0.05

VALID RANGES:
- Minimum scale: 0.05 (smallest prop)
- Maximum scale: 0.30 (largest building)
- Most entities should be between 0.08 and 0.20

Return ONLY a JSON array like:
[["cloud_1", 0.09], ["sun", 0.12], ["person", 0.13]]

Format: [entity_name, scale] where scale is a float."""

        try:
            response = self.client.generate(prompt, json_mode=True)
            result = json.loads(response)
            
            # Handle different response formats
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, list):
                        result = value
                        break
            
            # Validate and clamp
            validated = []
            entity_names = [e['name'] for e in entities]
            
            for item in result:
                if isinstance(item, list) and len(item) == 2:
                    entity_name = str(item[0])
                    scale = item[1]
                    
                    # Handle if scale is a list
                    if isinstance(scale, list):
                        scale = scale[0] if scale else 0.1
                    
                    try:
                        scale = float(scale)
                    except (ValueError, TypeError):
                        continue
                    
                    # Match entity name (handle suffixes)
                    matched_name = None
                    for en in entity_names:
                        llm_base = entity_name.split('_')[0] if '_' in entity_name else entity_name
                        entity_base = en.split('_')[0] if '_' in en else en
                        if llm_base == entity_base:
                            matched_name = en
                            break
                    
                    if matched_name:
                        # Clamp to reasonable range
                        scale = max(0.05, min(0.30, scale))
                        validated.append((matched_name, scale))
            
            return validated
            
        except Exception as e:
            print(f"  [ERROR] Chunk 6 failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")
            return [(e['name'], e.get('scale', 0.1)) for e in entities]

    def chunk7_collision_resolution(self, entities: List[Dict[str, Any]], positions: List[Tuple[str, float, float]], scales: List[Tuple[str, float]]) -> List[Tuple[str, float, float]]:
        """
        Chunk 7: Detect and resolve collisions between entities.
        
        This chunk checks for overlapping entities and suggests adjusted positions
        to resolve conflicts while maintaining composition quality.
        
        Considerations:
- Bounding box collision detection
- Minimum spacing requirements
- Maintaining ground line for characters
- Preserving visual relationships
- Small adjustments only (don't completely rearrange)
- Priority for main subject (move supporting elements first)
        
        Args:
            entities: List of entity dicts
            positions: List of (entity_name, x, y) tuples
            scales: List of (entity_name, scale) tuples
            
        Returns:
            List of (entity_name, x, y) tuples with adjusted positions
        """
        # Build detailed collision context
        entity_info = []
        for e in entities:
            # Find position and scale
            pos = next((p for p in positions if p[0] == e['name']), None)
            scl = next((s for s in scales if s[0] == e['name']), None)
            
            if pos and scl:
                x, y = pos[1], pos[2]
                scale = scl[1]
                # Estimate dimensions
                width = scale * 10
                height = scale * 10
                
                info = f"- {e['name']}"
                info += f" (x={x:.2f}, y={y:.2f}, scale={scale:.2f})"
                info += f", width≈{width:.2f}, height≈{height:.2f}"
                info += f", zone={e['zone']}, category={e['category']}"
                if e['zone'] == 'ground':
                    info += " [MUST stay on ground line]"
                entity_info.append(info)

        entity_list = "\n".join(entity_info)

        prompt = f"""Check these entities for overlaps and suggest minimal position fixes.

Entities:
{entity_list}

Rules:
- Overlap if: x distance < (width1+width2)/2 AND y distance < (height1+height2)/2
- Minimum spacing: characters 0.8, buildings 1.5, trees 1.2, vehicles 1.5, sky 0.5
- Adjust by 0.1-0.5 units only
- Keep ground entities at y = {self.ground_y}
- Keep within bounds: x ±{self.frame_width/2}, y {self.ground_y_min} to {self.sky_y_max}

Return ONLY JSON array of entities needing adjustment:
[["cloud_1", -3.5, 2.8], ["person", 1.0, -2.35]]

Format: [entity_name, x, y]. Empty array if no collisions."""

        try:
            # Chunk 7 is complex collision detection - use longer timeout (2 minutes)
            response = self.client.generate(prompt, json_mode=True, timeout=180)
            result = json.loads(response)
            
            # Handle different response formats
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, list):
                        result = value
                        break
            
            # Validate and clamp
            validated = []
            for item in result:
                if isinstance(item, list) and len(item) == 3:
                    entity_name = str(item[0])
                    x = float(item[1])
                    y = float(item[2])
                    # Clamp to bounds
                    x = max(-self.frame_width/2 + self.safe_margin_x, 
                           min(self.frame_width/2 - self.safe_margin_x, x))
                    y = max(self.ground_y_min, 
                           min(self.sky_y_max, y))
                    validated.append((entity_name, x, y))
            
            return validated
            
        except Exception as e:
            print(f"  [ERROR] Chunk 7 failed: {str(e).encode('ascii', 'ignore').decode('ascii')}")
            return positions  # Return original positions on failure

    def _fallback_z_index(self, entities: List[Dict[str, Any]]) -> List[Tuple[str, int]]:
        """
        Sophisticated fallback for z-index based on category and relationships.
        """
        z_map = {
            "sky_entity": 1,
            "structure": 2,
            "vehicle": 3,
            "prop": 4,
            "character": 5,
        }
        
        result = []
        for e in entities:
            base_z = z_map.get(e['category'], 3)
            
            # Adjust based on relationships
            if e.get('relation') == 'inside':
                base_z += 1  # Inside = in front
            elif e.get('relation') == 'behind':
                base_z -= 1  # Behind = further back
            elif e.get('relation') == 'in_front':
                base_z += 1  # In front = closer
            
            # Clamp
            base_z = max(1, min(10, base_z))
            result.append((e['name'], base_z))
        
        result.sort(key=lambda x: x[1])
        return result

    def _fallback_sky_distribution(self, entities: List[Dict[str, Any]]) -> List[Tuple[str, float, float]]:
        """
        Sophisticated fallback for sky distribution using natural patterns.
        """
        count = len(entities)
        if count == 0:
            return []
        
        result = []
        
        # Use golden ratio for natural distribution
        golden_ratio = (1 + math.sqrt(5)) / 2
        
        for i, e in enumerate(entities):
            # Spread x across frame with variation
            x = -self.frame_width/2 + self.safe_margin_x + (i * (self.frame_width - 2*self.safe_margin_x) / max(count - 1, 1))
            
            # Vary y using sine wave for organic look
            y = 2.0 + math.sin(i * math.pi / max(count, 1)) * 1.0
            
            # Add slight randomness
            import random
            x += random.uniform(-0.3, 0.3)
            y += random.uniform(-0.2, 0.2)
            
            # Clamp
            x = max(-self.frame_width/2 + self.safe_margin_x, 
                   min(self.frame_width/2 - self.safe_margin_x, x))
            y = max(self.sky_y_min + self.safe_margin_y, 
                   min(self.sky_y_max - self.safe_margin_y, y))
            
            result.append((e['name'], x, y))
        
        return result

    def _fallback_ground_distribution(self, entities: List[Dict[str, Any]]) -> List[Tuple[str, float, float]]:
        """
        Sophisticated fallback for ground distribution with proper spacing.
        """
        count = len(entities)
        if count == 0:
            return []
        
        result = []
        
        # Separate by category for better distribution
        characters = [e for e in entities if e['category'] == 'character']
        structures = [e for e in entities if e['category'] == 'structure']
        vehicles = [e for e in entities if e['category'] == 'vehicle']
        props = [e for e in entities if e['category'] == 'prop']
        
        # Distribute each category
        for i, e in enumerate(characters):
            x = -3 + (i * 6 / max(len(characters) - 1, 1))
            y = self.ground_y  # Characters on ground line
            result.append((e['name'], x, y))
        
        for i, e in enumerate(structures):
            x = -5 + (i * 10 / max(len(structures) - 1, 1))
            y = self.ground_y  # Structures on ground line
            result.append((e['name'], x, y))
        
        for i, e in enumerate(vehicles):
            x = -4 + (i * 8 / max(len(vehicles) - 1, 1))
            y = self.ground_y  # Vehicles on ground line
            result.append((e['name'], x, y))
        
        for i, e in enumerate(props):
            x = -2 + (i * 4 / max(len(props) - 1, 1))
            y = self.ground_y  # Props on ground line
            result.append((e['name'], x, y))
        
        return result
