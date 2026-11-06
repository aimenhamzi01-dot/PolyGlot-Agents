"""ISO-639 language-code normalization shared by multilingual tools."""
from __future__ import annotations


def canonical_iso639(tag: str) -> str:
    """Return a canonical ISO 639-1 code where available, otherwise ISO 639-3.

    Accepts ISO codes or BCP-47 tags such as ``pt-BR``. Region/script subtags
    belong in metadata, not in dataset directory names. Requires langcodes.
    """
    try:
        import langcodes
    except ImportError as exc:
        raise RuntimeError("Install project dependencies: pip install -r scripts/requirements.txt") from exc
    value = str(tag).strip().replace("_", "-")
    if not value or value.lower() in {"und", "unknown", "xx"}:
        return "und"
    language = langcodes.Language.get(value)
    if not language.is_valid():
        raise ValueError(f"Not a registered ISO 639 language tag: {tag!r}")
    # langcodes canonicalizes known ISO 639-3 forms to the preferred alpha-2
    # subtag (e.g. eng -> en) while retaining alpha-3 where no alpha-2 exists.
    return language.language.lower()


def is_iso639(code: str) -> bool:
    try:
        normalized = canonical_iso639(code)
        return normalized != "und" and normalized == code.lower()
    except (ValueError, RuntimeError):
        return False
