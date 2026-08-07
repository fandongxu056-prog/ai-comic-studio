"""Celery tasks for AI image generation."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_keyframe_image(self, shot_id: str, prompt: str, negative_prompt: str, seed: int, **kwargs):
    """Generate a keyframe image for a storyboard shot."""
    # Will be implemented with provider-specific logic in Step 4-6
    pass


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_character_reference(self, character_id: str, prompt: str, **kwargs):
    """Generate a character reference sheet image."""
    pass


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def generate_scene_reference(self, location_id: str, prompt: str, **kwargs):
    """Generate a scene/location reference image."""
    pass
