"""Scene parser - extracts entities, counts, relationships, and actions from natural language."""

import re
from dataclasses import dataclass, field
from typing import Any

from scene_dictionaries import (
    ENTITY_DICTIONARY,
    PLURAL_MAPPINGS,
    NUMBER_WORDS,
    ADJECTIVES,
    MOTION_VERBS,
    STATIC_VERBS,
    DIRECTION_WORDS,
)
from action_dictionary import ACTION_DICTIONARY, DIRECTION_MODIFIERS
from relationship_dictionary import (
    RELATIONSHIP_DICTIONARY,
    MULTI_WORD_PREPOSITIONS,
    SINGLE_WORD_PREPOSITIONS,
    PREPOSITION_PATTERNS,
    CLIP_RELATIONSHIPS,
    ANCHOR_RELATIONSHIPS,
)


@dataclass
class Entity:
    """Represents a single entity in the scene."""
    name: str
    count: int = 1
    asset: str = ""
    role: str = ""
    zone: str = ""
    default_scale: float = 0.1
    category: str = ""
    can_contain: bool = False
    container_type: str = ""
    default_relation: str = ""
    action: str = ""
    motion_type: str = "static"
    motion_direction: str | None = None
    motion_speed: float = 0.0
    relation: str = ""
    relation_target: str = ""
    relation_clip: bool = False
    relation_anchor: str = ""
    x_offset: float = 0.0
    y_offset: float = 0.0
    z_index: int = 0


@dataclass
class SceneSpec:
    """Complete scene specification."""
    description: str
    entities: list[Entity] = field(default_factory=list)
    scene_name: str = "Generated Scene"


class SceneParser:
    """Parses natural language descriptions into scene specifications."""

    def __init__(self):
        self.entity_dict = ENTITY_DICTIONARY
        self.plural_mappings = PLURAL_MAPPINGS
        self.number_words = NUMBER_WORDS
        self.adjectives = ADJECTIVES
        self.motion_verbs = MOTION_VERBS
        self.static_verbs = STATIC_VERBS
        self.direction_words = DIRECTION_WORDS
        self.action_dict = ACTION_DICTIONARY
        self.direction_modifiers = DIRECTION_MODIFIERS
        self.relationship_dict = RELATIONSHIP_DICTIONARY
        self.multi_word_preps = MULTI_WORD_PREPOSITIONS
        self.single_word_preps = SINGLE_WORD_PREPOSITIONS
        self.preposition_patterns = PREPOSITION_PATTERNS
        self.clip_relationships = CLIP_RELATIONSHIPS
        self.anchor_relationships = ANCHOR_RELATIONSHIPS

    def parse(self, description: str) -> SceneSpec:
        """Parse a natural language description into a scene spec."""
        # Normalize description
        description = description.lower().strip()

        # Tokenize
        tokens = self._tokenize(description)

        # Extract entities with counts
        entities = self._extract_entities(tokens, description)

        # Extract actions for each entity
        entities = self._extract_actions(entities, tokens, description)

        # Extract relationships
        entities = self._extract_relationships(entities, description)

        # Build scene spec
        spec = SceneSpec(
            description=description,
            entities=entities,
            scene_name=self._generate_scene_name(description),
        )

        return spec

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize text into words."""
        # Remove punctuation except hyphens
        text = re.sub(r"[^\w\s-]", " ", text)
        # Split on whitespace
        tokens = text.split()
        return tokens

    def _extract_entities(self, tokens: list[str], description: str) -> list[Entity]:
        """Extract entities with counts from tokens."""
        entities = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Check if token is a number word
            if token in self.number_words:
                count = self.number_words[token]
                # Look ahead for noun (skip adjectives)
                j = i + 1
                while j < len(tokens) and tokens[j] in self.adjectives:
                    j += 1
                if j < len(tokens):
                    noun = tokens[j]
                    entity = self._create_entity(noun, count, description)
                    if entity:
                        entities.append(entity)
                    i = j + 1
                    continue

            # Check if token is a digit
            if token.isdigit():
                count = int(token)
                # Look ahead for noun (skip adjectives)
                j = i + 1
                while j < len(tokens) and tokens[j] in self.adjectives:
                    j += 1
                if j < len(tokens):
                    noun = tokens[j]
                    entity = self._create_entity(noun, count, description)
                    if entity:
                        entities.append(entity)
                    i = j + 1
                    continue

            # Check if token is a noun
            entity = self._create_entity(token, 1, description)
            if entity:
                entities.append(entity)

            i += 1

        # Handle plurals without explicit numbers
        entities = self._handle_plurals(entities, tokens)

        return entities

    def _create_entity(self, noun: str, count: int, description: str) -> Entity | None:
        """Create an entity from a noun."""
        # Normalize noun (handle plurals)
        normalized = self._normalize_noun(noun)

        # Look up in dictionary
        if normalized not in self.entity_dict:
            return None

        info = self.entity_dict[normalized]

        entity = Entity(
            name=normalized,
            count=count,
            asset=info["asset"],
            role=info["role"],
            zone=info["zone"],
            default_scale=info["default_scale"],
            category=info.get("category", ""),
            can_contain=info.get("can_contain", False),
            container_type=info.get("container_type", ""),
            default_relation=info.get("default_relation", ""),
        )

        return entity

    def _normalize_noun(self, noun: str) -> str:
        """Normalize noun (handle plurals)."""
        noun = noun.lower()

        # Check plural mappings
        if noun in self.plural_mappings:
            return self.plural_mappings[noun]

        # Check if it's already singular
        if noun in self.entity_dict:
            return noun

        # Try removing 's' for simple plurals
        if noun.endswith("s") and noun[:-1] in self.entity_dict:
            return noun[:-1]

        # Try removing 'es' for plurals
        if noun.endswith("es") and noun[:-2] in self.entity_dict:
            return noun[:-2]

        # Try removing 'ies' for plurals (e.g., "cities" -> "city")
        if noun.endswith("ies") and noun[:-3] + "y" in self.entity_dict:
            return noun[:-3] + "y"

        return noun

    def _handle_plurals(self, entities: list[Entity], tokens: list[str]) -> list[Entity]:
        """Handle plurals without explicit numbers."""
        # Group entities by name
        entity_groups: dict[str, list[Entity]] = {}
        for entity in entities:
            if entity.name not in entity_groups:
                entity_groups[entity.name] = []
            entity_groups[entity.name].append(entity)

        # For each group, if count is 1 but noun was plural, set count to 2
        result = []
        for name, group in entity_groups.items():
            # Check if original token was plural
            is_plural = False
            for token in tokens:
                if token == name or token == name + "s" or token == name + "es":
                    if token != name:
                        is_plural = True
                        break

            if is_plural and len(group) == 1 and group[0].count == 1:
                group[0].count = 2  # Default plural count

            result.extend(group)

        return result

    def _extract_actions(self, entities: list[Entity], tokens: list[str], description: str) -> list[Entity]:
        """Extract actions for each entity."""
        for entity in entities:
            # Find verbs near the entity
            action = self._find_action_for_entity(entity, tokens, description)
            if action:
                entity.action = action
                entity.motion_type = action.get("motion_type", "static")
                entity.motion_direction = action.get("direction")
                entity.motion_speed = action.get("speed", 0.0)

        return entities

    def _find_action_for_entity(self, entity: Entity, tokens: list[str], description: str) -> dict[str, Any] | None:
        """Find action for a specific entity."""
        # Look for verbs in the description
        for token in tokens:
            # Check if token is a verb
            if token in self.action_dict:
                action_info = self.action_dict[token]
                # Check if this action is associated with this entity
                # Simple heuristic: if entity name appears near the verb
                entity_name = entity.name
                if entity_name in description:
                    # Check if verb is within 5 words of entity
                    words = description.split()
                    entity_idx = words.index(entity_name) if entity_name in words else -1
                    verb_idx = words.index(token) if token in words else -1

                    if entity_idx != -1 and verb_idx != -1:
                        if abs(entity_idx - verb_idx) <= 5:
                            return action_info

        # Check for direction modifiers (only if there's already a motion)
        if entity.motion_type != "static":
            for token in tokens:
                if token in self.direction_modifiers:
                    modifier = self.direction_modifiers[token]
                    # Apply direction modifier to existing action
                    entity.motion_direction = modifier.get("direction", entity.motion_direction)
                    entity.motion_speed *= modifier.get("speed_multiplier", 1.0)
                    return {
                        "motion_type": entity.motion_type,
                        "direction": entity.motion_direction,
                        "speed": entity.motion_speed,
                        "description": f"moving {modifier.get('direction', '')}",
                    }

        return None

    def _extract_relationships(self, entities: list[Entity], description: str) -> list[Entity]:
        """Extract relationships between entities."""
        # Find all prepositional phrases
        relationships = self._find_prepositional_phrases(description)

        # Assign relationships to entities
        for entity in entities:
            # Check if entity has a default relation
            if entity.default_relation:
                entity.relation = entity.default_relation
                entity.relation_clip = entity.default_relation in self.clip_relationships
                entity.relation_anchor = entity.default_relation if entity.default_relation in self.anchor_relationships else ""

            # Check for explicit relationships
            for rel in relationships:
                if rel["target"] == entity.name or entity.name in rel.get("targets", []):
                    entity.relation = rel["relation"]
                    entity.relation_target = rel.get("target_entity", "")
                    entity.relation_clip = rel["relation"] in self.clip_relationships
                    entity.relation_anchor = rel["relation"] if rel["relation"] in self.anchor_relationships else ""
                    break

        return entities

    def _find_prepositional_phrases(self, description: str) -> list[dict[str, Any]]:
        """Find all prepositional phrases in the description."""
        relationships = []

        # Check multi-word prepositions first
        for prep in self.multi_word_preps:
            if prep in description:
                # Find the target after the preposition
                pattern = rf"{re.escape(prep)}\s+(?:the\s+)?(\w+)"
                match = re.search(pattern, description)
                if match:
                    target = match.group(1)
                    normalized_target = self._normalize_noun(target)

                    rel_info = self.relationship_dict.get(prep, {})
                    relationships.append({
                        "relation": rel_info.get("relation", prep),
                        "target": normalized_target,
                        "target_entity": normalized_target,
                        "clip": rel_info.get("clip", False),
                        "anchor": rel_info.get("anchor", ""),
                    })

        # Check single-word prepositions
        for prep in self.single_word_preps:
            # Use word boundaries to avoid substring matches
            pattern = rf"\b{re.escape(prep)}\b\s+(?:the\s+)?(\w+)"
            matches = re.finditer(pattern, description)
            for match in matches:
                target = match.group(1)
                normalized_target = self._normalize_noun(target)

                rel_info = self.relationship_dict.get(prep, {})
                relationships.append({
                    "relation": rel_info.get("relation", prep),
                    "target": normalized_target,
                    "target_entity": normalized_target,
                    "clip": rel_info.get("clip", False),
                    "anchor": rel_info.get("anchor", ""),
                })

        return relationships

    def _generate_scene_name(self, description: str) -> str:
        """Generate a scene name from the description."""
        # Take first few words
        words = description.split()[:5]
        name = " ".join(words)
        # Capitalize and clean up
        name = name.title()
        name = re.sub(r"[^\w\s]", "", name)
        return name if name else "Generated Scene"

    def to_json(self, spec: SceneSpec) -> dict[str, Any]:
        """Convert scene spec to JSON-serializable dict."""
        entities = []
        for entity in spec.entities:
            entity_dict = {
                "name": entity.name,
                "count": entity.count,
                "asset": entity.asset,
                "role": entity.role,
                "zone": entity.zone,
                "scale_fraction": entity.default_scale,
                "category": entity.category,
                "can_contain": entity.can_contain,
                "container_type": entity.container_type,
                "action": entity.action,
                "motion_type": entity.motion_type,
                "motion_direction": entity.motion_direction,
                "motion_speed": entity.motion_speed,
                "relation": entity.relation,
                "relation_target": entity.relation_target,
                "relation_clip": entity.relation_clip,
                "relation_anchor": entity.relation_anchor,
                "x_offset": entity.x_offset,
                "y_offset": entity.y_offset,
                "z_index": entity.z_index,
            }
            entities.append(entity_dict)

        return {
            "scene_name": spec.scene_name,
            "description": spec.description,
            "entities": entities,
        }
