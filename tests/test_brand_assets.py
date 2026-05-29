"""Validate the bundled brand/ assets served by HA's Brands Proxy API.

Since HA 2026.3 custom integrations ship their own brand images under
``brand/`` and HA serves them at ``/api/brands/integration/<domain>/<image>``.
home-assistant/brands no longer accepts PRs for custom integrations, so this is
the only path to a non-placeholder icon.

The proxy resolves missing images through a fallback chain
(``homeassistant/components/brands`` ``IMAGE_FALLBACKS``): ``logo.png``,
``*@2x.png`` and the ``dark_*`` variants all fall back to ``icon.png`` before
ever reaching the CDN. So a single ``icon.png`` already covers every surface;
shipping ``logo.png``/``@2x`` copies would be pure redundancy.

The one variant worth shipping is ``dark_icon.png``: without it, dark-theme
surfaces fall back to the dark-ink ``icon.png``, which is barely visible on a
dark background. ``dark_logo.png`` in turn falls back to ``dark_icon.png``, so
this one file covers every dark surface too.

These tests therefore guard exactly the two files we ship, and — crucially —
assert their *content*, not just dimensions: a dark variant that is merely a
recolor gone wrong (a dark mark on a dark background, or the negative space
flattened to an opaque white block) is the original bug, so the suite fails
unless ``dark_icon.png`` is genuinely light where ``icon.png`` is dark *and*
keeps its negative space transparent.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

BRAND_DIR = (
    Path(__file__).parent.parent / "custom_components" / "abode_security" / "brand"
)

# The complete set we ship. Every other brand image resolves to icon.png (light
# surfaces) or dark_icon.png (dark surfaces) via the proxy's IMAGE_FALLBACKS.
BRAND_FILES = ("icon.png", "dark_icon.png")

# A pixel counts as "opaque" once its alpha clears this threshold; anti-aliased
# edge pixels below it are ignored when judging the mark's overall lightness.
_OPAQUE_ALPHA = 128


def _rgba_bytes(name: str) -> bytes:
    """Raw RGBA pixel bytes (4 per pixel) for a brand image."""
    with Image.open(BRAND_DIR / name) as img:
        return img.convert("RGBA").tobytes()


def _opaque_mean_luminance(name: str) -> float:
    """Mean perceptual luminance (0-255) of the image's opaque pixels."""
    raw = _rgba_bytes(name)
    total = 0.0
    count = 0
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
        if a < _OPAQUE_ALPHA:
            continue
        # Rec. 601 luma.
        total += 0.299 * r + 0.587 * g + 0.114 * b
        count += 1
    assert count, f"brand/{name} has no opaque pixels"
    return total / count


def _opaque_fraction(name: str) -> float:
    """Fraction (0-1) of pixels that are opaque (alpha >= _OPAQUE_ALPHA)."""
    raw = _rgba_bytes(name)
    pixels = len(raw) // 4
    opaque = sum(1 for i in range(3, len(raw), 4) if raw[i] >= _OPAQUE_ALPHA)
    return opaque / pixels


@pytest.mark.parametrize("name", BRAND_FILES)
def test_brand_file_exists(name: str) -> None:
    assert (BRAND_DIR / name).is_file(), f"missing brand asset: brand/{name}"


@pytest.mark.parametrize("name", BRAND_FILES)
def test_icon_is_256_square_rgba(name: str) -> None:
    with Image.open(BRAND_DIR / name) as img:
        assert img.size == (256, 256), f"brand/{name} must be 256x256, got {img.size}"
        # RGBA so the mark sits on any background.
        assert img.mode in ("RGBA", "LA") or "transparency" in img.info, (
            f"brand/{name} must have an alpha channel (got mode {img.mode})"
        )


def test_dark_icon_is_light_ink() -> None:
    """Regression guard for #153: the dark variant must be light, not a dark
    mark recolored onto transparency (which renders invisibly on dark themes)."""
    luminance = _opaque_mean_luminance("dark_icon.png")
    assert luminance > 192, (
        f"dark_icon.png opaque pixels should be light, mean luminance {luminance:.0f} "
        "— a dark dark_icon is invisible on dark themes and defeats the fix"
    )


def test_dark_icon_lighter_than_light_icon() -> None:
    """The dark variant must actually invert the mark's brightness, not just
    differ in some incidental way."""
    light = _opaque_mean_luminance("icon.png")
    dark = _opaque_mean_luminance("dark_icon.png")
    assert dark > light + 64, (
        f"dark_icon.png ({dark:.0f}) is not meaningfully lighter than "
        f"icon.png ({light:.0f}) — dark theme would show a near-invisible mark"
    )


def test_dark_icon_differs_from_light_icon() -> None:
    """The dark variant must be a real recolor, not a copy of icon.png."""
    light = (BRAND_DIR / "icon.png").read_bytes()
    dark = (BRAND_DIR / "dark_icon.png").read_bytes()
    assert light != dark, "dark_icon.png is byte-identical to icon.png"


def test_dark_icon_preserves_transparent_negative_space() -> None:
    """Regression guard for #153: the icon's baked-in negative space must stay
    transparent. A flattened, fully-opaque white PNG would pass the lightness
    checks above while rendering as a solid white square on the dark theme, so
    assert the mark covers only a minority of the canvas (the rest transparent).
    The real asset is ~20% opaque; a flattened square would be ~100%."""
    opaque = _opaque_fraction("dark_icon.png")
    assert opaque < 0.6, (
        f"dark_icon.png is {opaque:.0%} opaque — the transparent negative space "
        "was flattened, so it would render as a white block on dark themes"
    )
