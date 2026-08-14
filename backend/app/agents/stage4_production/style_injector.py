"""Dynamic style injection — maps art_style to prompt keywords.

Replaces the old hardcoded anime-only _ensure_anime_style().
All providers (image/video) use this to inject style-consistent keywords
based on the project's art_style preference.

Supported styles: anime, realistic, semi_realistic, cartoon, ink_wash,
comic_book, illustration, 3d_render, other.
"""

STYLE_PROFILES: dict[str, dict] = {
    "anime": {
        "prefix_cn": "日漫动画风格",
        "suffix_en": "anime art style, clean linework, flat color illustration",
        "constraints": [
            "consistent anime character design",
            "no realistic textures",
            "no 3D rendering",
            "no photographic details",
        ],
        "negative": "realistic, photorealistic, 3D render, photograph, hyper-realistic",
        "conflicting_terms": [
            "realistic", "photorealistic", "3D render", "3d render",
            "8k photo", "photograph", "hyper-realistic", "photo-realistic",
            "realistic face", "realistic skin",
        ],
        "motion_hints": "smooth anime-style motion, consistent character appearance",
    },
    "realistic": {
        "prefix_cn": "真人实拍电影风格",
        "suffix_en": "photorealistic, cinematic lighting, 8k detail, film still",
        "constraints": [
            "natural skin texture",
            "realistic proportions",
            "cinematic color grading",
            "shallow depth of field",
        ],
        "negative": "anime, cartoon, illustration, flat color, 2D, painting",
        "conflicting_terms": [
            "anime", "cartoon", "illustration", "flat color",
            "clean linework", "anime art style",
        ],
        "motion_hints": "natural human motion, cinematic movement, realistic physics",
    },
    "semi_realistic": {
        "prefix_cn": "半写实CG风格",
        "suffix_en": "semi-realistic, stylized realism, detailed rendering",
        "constraints": [
            "stylized realistic proportions",
            "high detail rendering",
            "cinematic lighting",
        ],
        "negative": "flat color, cartoon, pixel art, low detail",
        "conflicting_terms": ["cartoon", "flat color", "pixel art"],
        "motion_hints": "smooth stylized motion, cinematic movement",
    },
    "cartoon": {
        "prefix_cn": "美式卡通风格",
        "suffix_en": "cartoon style, bold outlines, vibrant colors",
        "constraints": [
            "bold clean outlines",
            "vibrant saturated colors",
            "stylized proportions",
        ],
        "negative": "photorealistic, realistic textures, 3D render",
        "conflicting_terms": ["photorealistic", "realistic textures", "3D render"],
        "motion_hints": "bouncy cartoon motion, exaggerated animation",
    },
    "ink_wash": {
        "prefix_cn": "水墨画风格",
        "suffix_en": "ink wash painting, brush strokes, chinese art",
        "constraints": [
            "flowing ink brush strokes",
            "traditional chinese painting",
            "paper texture",
        ],
        "negative": "photorealistic, 3D render, digital glossy",
        "conflicting_terms": ["photorealistic", "3D render", "glossy"],
        "motion_hints": "flowing ink diffusion, ethereal motion",
    },
    "comic_book": {
        "prefix_cn": "美漫漫画风格",
        "suffix_en": "comic book style, halftone shading, bold ink lines",
        "constraints": [
            "halftone dots",
            "bold ink outlines",
            "dramatic shading",
        ],
        "negative": "photorealistic, 3D render",
        "conflicting_terms": ["photorealistic", "3D render"],
        "motion_hints": "comic panel motion, dynamic action poses",
    },
    "illustration": {
        "prefix_cn": "精美插画风格",
        "suffix_en": "digital illustration, painterly, detailed artwork",
        "constraints": [
            "painterly brushwork",
            "rich color palette",
            "detailed illustration",
        ],
        "negative": "photorealistic, 3D render",
        "conflicting_terms": ["photorealistic", "3D render"],
        "motion_hints": "gentle illustrated motion, soft transitions",
    },
    "3d_render": {
        "prefix_cn": "3D渲染风格",
        "suffix_en": "3d render, octane render, subsurface scattering",
        "constraints": [
            "3d cgi rendering",
            "soft shadows",
            "subsurface scattering",
        ],
        "negative": "flat 2D, cartoon outlines, watercolor",
        "conflicting_terms": ["flat 2D", "cartoon outlines", "watercolor"],
        "motion_hints": "smooth 3d animation, physically based motion",
    },
}


class StyleInjector:
    """Injects style keywords into prompts based on art_style preference."""

    def __init__(self, art_style: str = "anime"):
        self.art_style = art_style
        self.profile = STYLE_PROFILES.get(art_style, STYLE_PROFILES["anime"])

    def clean_conflicting_terms(self, prompt: str) -> str:
        """Remove style terms that conflict with the target style."""
        cleaned = prompt
        for term in self.profile["conflicting_terms"]:
            cleaned = cleaned.replace(term, "")
            cleaned = cleaned.replace(term.capitalize(), "")
            cleaned = cleaned.replace(term.upper(), "")
        return cleaned

    def enhance_prompt(self, prompt: str, negative_prompt: str = "") -> str:
        """Build the final style-consistent prompt.

        1. Remove conflicting style terms
        2. Prefix with target style descriptor (Chinese)
        3. Append style constraints + suffix keywords
        4. Merge negative prompt as avoidance
        """
        cleaned = self.clean_conflicting_terms(prompt)

        parts: list[str] = []

        # 1. Style prefix
        prefix = self.profile["prefix_cn"]
        if prefix not in cleaned:
            parts.append(prefix)

        # 2. Negative as avoidance
        if negative_prompt:
            parts.append(f"(avoid: {negative_prompt[:120]})")

        # 3. Cleaned prompt
        parts.append(cleaned.strip())

        # 4. Style constraints + suffix
        parts.append(", ".join(self.profile["constraints"]))
        parts.append(self.profile["suffix_en"])

        return ", ".join(p for p in parts if p)

    def get_negative(self) -> str:
        """Global negative prompt for this style."""
        return self.profile["negative"]

    def get_motion_hints(self) -> str:
        """Motion description hints for video generation."""
        return self.profile["motion_hints"]

    def enhance_motion_prompt(self, motion: str) -> str:
        """Enhance a video motion prompt with style-appropriate hints."""
        base = motion.strip() if motion else ""
        hints = self.get_motion_hints()
        if base:
            return f"{base}. {hints}"
        return f"{hints}, subtle natural movement"


# Backwards-compatible helper (existing code paths use _ensure_anime_style)
def ensure_anime_style(prompt: str, negative_prompt: str = "") -> str:
    """Legacy helper — kept for compatibility with older callers."""
    injector = StyleInjector("anime")
    return injector.enhance_prompt(prompt, negative_prompt)
