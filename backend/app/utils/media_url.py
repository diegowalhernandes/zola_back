def sanitize_media_url(url: str | None) -> str | None:
    """Remove URLs locais salvas por engano no banco (dev apontando para prod)."""
    if not url or not url.strip():
        return None

    lower = url.strip().lower()
    if "localhost" in lower or "127.0.0.1" in lower or "0.0.0.0" in lower:
        return None

    return url.strip()
