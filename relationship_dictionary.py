"""Relationship dictionary with prepositions and spatial relationships."""

from typing import Any


# Relationship dictionary: maps prepositions to spatial relationships
RELATIONSHIP_DICTIONARY: dict[str, dict[str, Any]] = {
    # Containment relationships
    "inside": {
        "relation": "inside",
        "clip": True,
        "anchor": "container",
        "description": "inside container",
    },
    "in": {
        "relation": "inside",
        "clip": True,
        "anchor": "container",
        "description": "in container",
    },
    "within": {
        "relation": "inside",
        "clip": True,
        "anchor": "container",
        "description": "within container",
    },
    "into": {
        "relation": "inside",
        "clip": True,
        "anchor": "container",
        "description": "into container",
    },

    # Position relationships
    "on": {
        "relation": "on_top",
        "clip": False,
        "anchor": "surface",
        "description": "on top of",
    },
    "on_top_of": {
        "relation": "on_top",
        "clip": False,
        "anchor": "surface",
        "description": "on top of",
    },
    "above": {
        "relation": "above",
        "clip": False,
        "anchor": "above",
        "description": "above",
    },
    "over": {
        "relation": "above",
        "clip": False,
        "anchor": "above",
        "description": "over",
    },
    "below": {
        "relation": "below",
        "clip": False,
        "anchor": "below",
        "description": "below",
    },
    "under": {
        "relation": "below",
        "clip": False,
        "anchor": "below",
        "description": "under",
    },
    "beneath": {
        "relation": "below",
        "clip": False,
        "anchor": "below",
        "description": "beneath",
    },

    # Adjacency relationships
    "next_to": {
        "relation": "adjacent",
        "clip": False,
        "anchor": "adjacent",
        "description": "next to",
    },
    "beside": {
        "relation": "adjacent",
        "clip": False,
        "anchor": "adjacent",
        "description": "beside",
    },
    "near": {
        "relation": "adjacent",
        "clip": False,
        "anchor": "adjacent",
        "description": "near",
    },
    "close_to": {
        "relation": "adjacent",
        "clip": False,
        "anchor": "adjacent",
        "description": "close to",
    },
    "by": {
        "relation": "adjacent",
        "clip": False,
        "anchor": "adjacent",
        "description": "by",
    },
    "at": {
        "relation": "adjacent",
        "clip": False,
        "anchor": "adjacent",
        "description": "at",
    },

    # Behind/in front relationships
    "behind": {
        "relation": "behind",
        "clip": True,
        "anchor": "behind",
        "description": "behind",
    },
    "in_front_of": {
        "relation": "in_front",
        "clip": False,
        "anchor": "in_front",
        "description": "in front of",
    },
    "before": {
        "relation": "in_front",
        "clip": False,
        "anchor": "in_front",
        "description": "before",
    },
    "after": {
        "relation": "behind",
        "clip": True,
        "anchor": "behind",
        "description": "after",
    },

    # Between/among relationships
    "between": {
        "relation": "between",
        "clip": False,
        "anchor": "between",
        "description": "between",
    },
    "among": {
        "relation": "among",
        "clip": False,
        "anchor": "among",
        "description": "among",
    },
    "amid": {
        "relation": "among",
        "clip": False,
        "anchor": "among",
        "description": "amid",
    },
    "amidst": {
        "relation": "among",
        "clip": False,
        "anchor": "among",
        "description": "amidst",
    },

    # Directional relationships
    "to": {
        "relation": "direction",
        "clip": False,
        "anchor": "direction",
        "description": "to",
    },
    "toward": {
        "relation": "direction",
        "clip": False,
        "anchor": "direction",
        "description": "toward",
    },
    "towards": {
        "relation": "direction",
        "clip": False,
        "anchor": "direction",
        "description": "towards",
    },
    "from": {
        "relation": "direction",
        "clip": False,
        "anchor": "direction",
        "description": "from",
    },
    "away_from": {
        "relation": "direction",
        "clip": False,
        "anchor": "direction",
        "description": "away from",
    },

    # With/without relationships (only use as conjunctions, not spatial)
    "with": {
        "relation": "with",
        "clip": False,
        "anchor": "with",
        "description": "with (conjunction)",
        "is_conjunction": True,
    },
    "without": {
        "relation": "without",
        "clip": False,
        "anchor": "without",
        "description": "without (conjunction)",
        "is_conjunction": True,
    },
    "and": {
        "relation": "and",
        "clip": False,
        "anchor": "and",
        "description": "and (conjunction)",
        "is_conjunction": True,
    },
    "or": {
        "relation": "or",
        "clip": False,
        "anchor": "or",
        "description": "or (conjunction)",
        "is_conjunction": True,
    },

    # Through/across relationships
    "through": {
        "relation": "through",
        "clip": False,
        "anchor": "through",
        "description": "through",
    },
    "across": {
        "relation": "across",
        "clip": False,
        "anchor": "across",
        "description": "across",
    },
    "along": {
        "relation": "along",
        "clip": False,
        "anchor": "along",
        "description": "along",
    },
    "around": {
        "relation": "around",
        "clip": False,
        "anchor": "around",
        "description": "around",
    },
    "about": {
        "relation": "about",
        "clip": False,
        "anchor": "about",
        "description": "about",
    },

    # Special relationships
    "looking_at": {
        "relation": "looking_at",
        "clip": False,
        "anchor": "looking_at",
        "description": "looking at",
    },
    "watching": {
        "relation": "watching",
        "clip": False,
        "anchor": "watching",
        "description": "watching",
    },
    "staring_at": {
        "relation": "staring_at",
        "clip": False,
        "anchor": "staring_at",
        "description": "staring at",
    },
    "gazing_at": {
        "relation": "gazing_at",
        "clip": False,
        "anchor": "gazing_at",
        "description": "gazing at",
    },
    "pointing_at": {
        "relation": "pointing_at",
        "clip": False,
        "anchor": "pointing_at",
        "description": "pointing at",
    },
    "facing": {
        "relation": "facing",
        "clip": False,
        "anchor": "facing",
        "description": "facing",
    },
    "toward": {
        "relation": "toward",
        "clip": False,
        "anchor": "toward",
        "description": "toward",
    },
}


# Multi-word prepositions (must be checked before single words)
MULTI_WORD_PREPOSITIONS: list[str] = [
    "in front of",
    "next to",
    "close to",
    "on top of",
    "away from",
    "looking at",
    "watching",
    "staring at",
    "gazing at",
    "pointing at",
]


# Single-word prepositions
SINGLE_WORD_PREPOSITIONS: list[str] = [
    "inside", "in", "within", "into",
    "on", "above", "over", "below", "under", "beneath",
    "behind", "before", "after",
    "between", "among", "amid", "amidst",
    "to", "toward", "towards", "from",
    "with", "without", "and", "or",
    "through", "across", "along", "around", "about",
    "at", "by", "near", "beside",
    "facing", "toward",
]


# Preposition patterns for parsing
PREPOSITION_PATTERNS: list[tuple[str, str]] = [
    # (pattern, relationship_type)
    (r"\binside\s+(?:the\s+)?(\w+)", "inside"),
    (r"\bin\s+(?:the\s+)?(\w+)", "inside"),
    (r"\bwithin\s+(?:the\s+)?(\w+)", "inside"),
    (r"\binto\s+(?:the\s+)?(\w+)", "inside"),
    (r"\bon\s+(?:the\s+)?(\w+)", "on_top"),
    (r"\bon\s+top\s+of\s+(?:the\s+)?(\w+)", "on_top"),
    (r"\babove\s+(?:the\s+)?(\w+)", "above"),
    (r"\bover\s+(?:the\s+)?(\w+)", "above"),
    (r"\bbelow\s+(?:the\s+)?(\w+)", "below"),
    (r"\bunder\s+(?:the\s+)?(\w+)", "below"),
    (r"\bbeneath\s+(?:the\s+)?(\w+)", "below"),
    (r"\bnext\s+to\s+(?:the\s+)?(\w+)", "adjacent"),
    (r"\bbeside\s+(?:the\s+)?(\w+)", "adjacent"),
    (r"\bnear\s+(?:the\s+)?(\w+)", "adjacent"),
    (r"\bclose\s+to\s+(?:the\s+)?(\w+)", "adjacent"),
    (r"\bby\s+(?:the\s+)?(\w+)", "adjacent"),
    (r"\bat\s+(?:the\s+)?(\w+)", "adjacent"),
    (r"\bbehind\s+(?:the\s+)?(\w+)", "behind"),
    (r"\bin\s+front\s+of\s+(?:the\s+)?(\w+)", "in_front"),
    (r"\bbefore\s+(?:the\s+)?(\w+)", "in_front"),
    (r"\bafter\s+(?:the\s+)?(\w+)", "behind"),
    (r"\bbetween\s+(?:the\s+)?(\w+)\s+and\s+(?:the\s+)?(\w+)", "between"),
    (r"\bamong\s+(?:the\s+)?(\w+)", "among"),
    (r"\bamid\s+(?:the\s+)?(\w+)", "among"),
    (r"\bamidst\s+(?:the\s+)?(\w+)", "among"),
    (r"\bto\s+(?:the\s+)?(\w+)", "direction"),
    (r"\btoward\s+(?:the\s+)?(\w+)", "direction"),
    (r"\btowards\s+(?:the\s+)?(\w+)", "direction"),
    (r"\bfrom\s+(?:the\s+)?(\w+)", "direction"),
    (r"\baway\s+from\s+(?:the\s+)?(\w+)", "direction"),
    (r"\bwith\s+(?:the\s+)?(\w+)", "with"),
    (r"\bwithout\s+(?:the\s+)?(\w+)", "without"),
    (r"\bthrough\s+(?:the\s+)?(\w+)", "through"),
    (r"\bacross\s+(?:the\s+)?(\w+)", "across"),
    (r"\balong\s+(?:the\s+)?(\w+)", "along"),
    (r"\baround\s+(?:the\s+)?(\w+)", "around"),
    (r"\babout\s+(?:the\s+)?(\w+)", "about"),
    (r"\blooking\s+at\s+(?:the\s+)?(\w+)", "looking_at"),
    (r"\bwatching\s+(?:the\s+)?(\w+)", "watching"),
    (r"\bstaring\s+at\s+(?:the\s+)?(\w+)", "staring_at"),
    (r"\bgazing\s+at\s+(?:the\s+)?(\w+)", "gazing_at"),
    (r"\bpointing\s+at\s+(?:the\s+)?(\w+)", "pointing_at"),
    (r"\bfacing\s+(?:the\s+)?(\w+)", "facing"),
    (r"\btoward\s+(?:the\s+)?(\w+)", "toward"),
]


# Relationship types that require clipping
CLIP_RELATIONSHIPS: set[str] = {
    "inside",
    "behind",
}


# Relationship types that require anchoring
ANCHOR_RELATIONSHIPS: set[str] = {
    "inside",
    "on_top",
    "above",
    "below",
    "adjacent",
    "behind",
    "in_front",
    "between",
    "among",
    "looking_at",
    "watching",
    "staring_at",
    "gazing_at",
    "pointing_at",
    "facing",
    "toward",
}
