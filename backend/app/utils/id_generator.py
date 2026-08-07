"""Structured ID generator — follows the ID conventions defined in docs/schema-design.md."""


def generate_project_id() -> str:
    """Generate project ID: PRJ-{uuid_short}"""
    import uuid
    return f"PRJ-{uuid.uuid4().hex[:8].upper()}"


def generate_script_id() -> str:
    """Generate script ID: SCR-{uuid_short}"""
    import uuid
    return f"SCR-{uuid.uuid4().hex[:8].upper()}"


def generate_asset_set_id() -> str:
    """Generate asset set ID: AST-{uuid_short}"""
    import uuid
    return f"AST-{uuid.uuid4().hex[:8].upper()}"


def generate_storyboard_id() -> str:
    """Generate storyboard ID: STB-{uuid_short}"""
    import uuid
    return f"STB-{uuid.uuid4().hex[:8].upper()}"


def generate_production_id() -> str:
    """Generate production ID: PRD-{uuid_short}"""
    import uuid
    return f"PRD-{uuid.uuid4().hex[:8].upper()}"


def generate_character_id(index: int) -> str:
    """Generate character ID: CHAR-{index:04d}"""
    return f"CHAR-{index:04d}"


def generate_location_id(index: int) -> str:
    """Generate location ID: LOC-{index:04d}"""
    return f"LOC-{index:04d}"


def generate_prop_id(index: int) -> str:
    """Generate prop ID: PROP-{index:04d}"""
    return f"PROP-{index:04d}"


def generate_costume_id(index: int) -> str:
    """Generate costume ID: COST-{index:04d}"""
    return f"COST-{index:04d}"


def generate_scene_id(episode_index: int, scene_index: int) -> str:
    """Generate scene ID: SC-E{episode:03d}-S{scene:03d}"""
    return f"SC-E{episode_index:03d}-S{scene_index:03d}"


def generate_shot_id(episode_index: int, scene_index: int, shot_index: int) -> str:
    """Generate shot ID: SH-E{episode:03d}-S{scene:03d}-{shot:03d}"""
    return f"SH-E{episode_index:03d}-S{scene_index:03d}-{shot_index:03d}"


def generate_message_id() -> str:
    """Generate agent message ID: MSG-{uuid}"""
    import uuid
    return f"MSG-{uuid.uuid4()}"
