"""Celery tasks for AI video generation."""

from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def generate_shot_video(self, shot_id: str, start_frame_url: str, end_frame_url: str, motion_prompt: str, **kwargs):
    """Generate a video segment from keyframe images."""
    pass


@celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
def composite_episode_video(self, episode_index: int, shot_ids: list[str], output_path: str, **kwargs):
    """Composite all shot videos + audio + subtitles into final episode video."""
    pass
