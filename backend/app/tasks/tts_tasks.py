"""Celery tasks for TTS (text-to-speech) generation."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def generate_dialogue_audio(self, shot_id: str, character_id: str, text: str, voice_id: str, **kwargs):
    """Generate TTS audio for a dialogue segment."""
    pass


@celery_app.task(bind=True, max_retries=1)
def generate_bgm(self, episode_index: int, mood_description: str, duration_ms: int, **kwargs):
    """Generate background music for an episode."""
    pass
