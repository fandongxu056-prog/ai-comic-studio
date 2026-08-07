"""Global seed management system for visual consistency across stages.

Design (from docs/schema-design.md):
- Global seed (style_manifest) → character/location seeds → shot seeds
- Each level derives deterministically from the parent seed
- This ensures reproducible visual consistency across the entire pipeline
"""

import hashlib
from typing import Optional

# A prime number used for offsetting seeds to ensure variation
_PRIME_OFFSET = 7919


def generate_global_seed() -> int:
    """Generate a random global seed for a new project."""
    import random
    return random.randint(0, 2_147_483_647)


def derive_seed(global_seed: int, entity_id: str, offset: int = 0) -> int:
    """Derive a deterministic seed for an entity from the global seed.

    Args:
        global_seed: The project-level global seed.
        entity_id: Unique ID of the entity (character, location, prop, etc.).
        offset: Optional offset for variation (e.g., different costumes).

    Returns:
        A deterministic seed in [0, 2_147_483_647].
    """
    hashed = hashlib.sha256(f"{global_seed}:{entity_id}:{offset}".encode()).digest()
    derived = int.from_bytes(hashed[:4], byteorder="big")
    return derived % 2_147_483_647


def derive_shot_seed(global_seed: int, episode_index: int, scene_index: int, shot_index: int) -> int:
    """Derive a deterministic seed for a specific shot.

    Formula: global_seed + (episode * 1000 + scene * 100 + shot) * PRIME_OFFSET
    This ensures adjacent shots have different but related seeds.
    """
    offset = (episode_index * 1000 + scene_index * 100 + shot_index) * _PRIME_OFFSET
    return (global_seed + offset) % 2_147_483_647


def verify_seed_chain(global_seed: int, derived_seeds: dict[str, int]) -> bool:
    """Verify that a set of seeds was derived correctly from the global seed."""
    for entity_id, expected_seed in derived_seeds.items():
        actual_seed = derive_seed(global_seed, entity_id)
        if actual_seed != expected_seed:
            return False
    return True


class SeedManager:
    """Manages seed generation and derivation across the project lifecycle."""

    def __init__(self, global_seed: Optional[int] = None):
        self.global_seed = global_seed or generate_global_seed()

    def character_seed(self, character_id: str) -> int:
        return derive_seed(self.global_seed, character_id)

    def costume_seed(self, character_id: str, costume_id: str) -> int:
        return derive_seed(self.global_seed, f"{character_id}:{costume_id}")

    def location_seed(self, location_id: str) -> int:
        return derive_seed(self.global_seed, location_id)

    def prop_seed(self, prop_id: str) -> int:
        return derive_seed(self.global_seed, prop_id)

    def shot_seed(self, episode: int, scene: int, shot: int) -> int:
        return derive_shot_seed(self.global_seed, episode, scene, shot)
