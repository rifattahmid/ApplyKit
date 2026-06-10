import os
import re
from dataclasses import dataclass

try:
    import config
except ImportError:  # pragma: no cover - config.py is expected in normal use
    config = object()


# =============================================================================
# Project Paths
# =============================================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ExtendedSection:
    heading: str
    text: str


@dataclass
class ParsedExtendedContext:
    global_text: str
    sections: list[ExtendedSection]


@dataclass
class ExtendedContextSelection:
    text: str
    selected_count: int
    total_sections: int
    selected_headings: list[str]
    used_fallback: bool = False


# =============================================================================
# Path Resolution
# =============================================================================

def resolve_optional_project_path(path):
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def resolve_resume_markdown_path(category_dir=None, local_filename=None, fallback_path=None):
    candidates = []
    if category_dir and local_filename:
        candidates.append(os.path.join(category_dir, local_filename))
        country_dir = os.path.dirname(category_dir)
        if country_dir and country_dir != category_dir:
            candidates.append(os.path.join(country_dir, local_filename))

    resolved_fallback = resolve_optional_project_path(fallback_path)
    if resolved_fallback:
        candidates.append(resolved_fallback)

    return next((candidate for candidate in candidates if os.path.exists(candidate)), None)


# =============================================================================
# Resume Context Loading
# =============================================================================

def load_resume_markdown(category_dir=None, local_filename=None, fallback_path=None):
    source_path = resolve_resume_markdown_path(
        category_dir=category_dir,
        local_filename=local_filename,
        fallback_path=fallback_path,
    )
    if not source_path:
        return ""
    with open(source_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_resume_context_paths(
    category_dir=None,
    source_filename=None,
    extended_filename=None,
    project_source=None,
    project_extended=None,
):
    return {
        "source": resolve_resume_markdown_path(
            category_dir=category_dir,
            local_filename=source_filename if source_filename is not None else _setting("RESUME_SOURCE_FILENAME", "resume.source.md"),
            fallback_path=project_source if project_source is not None else _setting("RESUME_SOURCE", "resume.source.md"),
        ),
        "extended": resolve_resume_markdown_path(
            category_dir=category_dir,
            local_filename=extended_filename if extended_filename is not None else _setting("RESUME_EXTENDED_FILENAME", "resume.extended.md"),
            fallback_path=project_extended if project_extended is not None else _setting("RESUME_EXTENDED_SOURCE", "resume.extended.md"),
        ),
    }


def resume_context_status(context_paths, extended_selection=None):
    source_line = f"  Resume source of truth: {'Found' if context_paths.get('source') else 'Not found'}"
    if context_paths.get("extended") and extended_selection:
        extended_line = (
            "  Resume extended context: "
            f"Found, selected {extended_selection.selected_count}/{extended_selection.total_sections} sections"
        )
    else:
        extended_line = f"  Resume extended context: {'Found' if context_paths.get('extended') else 'Not found'}"
    return [source_line, extended_line]


# =============================================================================
# Public Source Helpers
# =============================================================================

def load_resume_source(path=None, category_dir=None, project_source=None, source_filename=None):
    fallback = project_source if project_source is not None else (path if path is not None else _setting("RESUME_SOURCE", "resume.source.md"))
    return load_resume_markdown(
        category_dir=category_dir,
        local_filename=source_filename if source_filename is not None else _setting("RESUME_SOURCE_FILENAME", "resume.source.md"),
        fallback_path=fallback,
    )


def load_resume_extended(path=None, category_dir=None, project_extended=None, extended_filename=None):
    fallback = project_extended if project_extended is not None else (path if path is not None else _setting("RESUME_EXTENDED_SOURCE", "resume.extended.md"))
    return load_resume_markdown(
        category_dir=category_dir,
        local_filename=extended_filename if extended_filename is not None else _setting("RESUME_EXTENDED_FILENAME", "resume.extended.md"),
        fallback_path=fallback,
    )


# =============================================================================
# Extended Context Querying
# =============================================================================

def build_resume_context_query(data, marked_sentences):
    parts = [
        data.get("title", ""),
        data.get("intro", ""),
        data.get("responsibilities", ""),
        data.get("qualifications", ""),
        "\n".join(marked_sentences),
    ]
    return "\n".join(part for part in parts if part)


# =============================================================================
# Extended Markdown Parsing
# =============================================================================

def parse_extended_markdown(text):
    cleaned = _remove_reference_section(text or "")
    first_section = re.search(r"(?m)^###\s+(.+?)\s*$", cleaned)
    if not first_section:
        return ParsedExtendedContext(global_text=cleaned.strip(), sections=[])

    global_text = cleaned[:first_section.start()].strip()
    section_text = cleaned[first_section.start():]
    matches = list(re.finditer(r"(?m)^###\s+(.+?)\s*$", section_text))
    sections = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section_text)
        heading = match.group(1).strip()
        body = section_text[start:end].strip()
        if heading.lower() == "theme name":
            continue
        sections.append(ExtendedSection(heading=heading, text=f"### {heading}\n\n{body}".strip()))
    return ParsedExtendedContext(global_text=global_text, sections=sections)


# =============================================================================
# Extended Context Selection
# =============================================================================

def select_resume_extended_context(
    extended_text,
    query_text,
    *,
    enabled=None,
    max_sections=None,
    max_chars=None,
    min_score=None,
):
    enabled = _bool_setting("RESUME_EXTENDED_SELECTION_ENABLED", True) if enabled is None else bool(enabled)
    max_sections = _int_setting("RESUME_EXTENDED_MAX_SECTIONS", 8, minimum=1) if max_sections is None else max(1, int(max_sections))
    max_chars = _int_setting("RESUME_EXTENDED_MAX_CHARS", 12000, minimum=1000) if max_chars is None else max(200, int(max_chars))
    min_score = _int_setting("RESUME_EXTENDED_MIN_SCORE", 2, minimum=0) if min_score is None else max(0, int(min_score))

    if not extended_text:
        return ExtendedContextSelection("", 0, 0, [], False)
    if not enabled:
        return ExtendedContextSelection(_cap_text(extended_text.strip(), max_chars), 0, 0, [], True)

    parsed = parse_extended_markdown(extended_text)
    if not parsed.sections:
        return ExtendedContextSelection(_cap_text(parsed.global_text or extended_text.strip(), max_chars), 0, 0, [], True)

    query_tokens = _tokens(query_text)
    scored = []
    for section in parsed.sections:
        score = _section_score(section, query_tokens, query_text)
        if score >= min_score:
            scored.append((score, section))

    scored.sort(key=lambda item: (-item[0], item[1].heading.lower()))
    selected_sections = [section for _, section in scored[:max_sections]]
    if not selected_sections:
        return ExtendedContextSelection(
            _cap_text(parsed.global_text or extended_text.strip(), max_chars),
            0,
            len(parsed.sections),
            [],
            True,
        )

    parts = []
    if parsed.global_text:
        parts.append(parsed.global_text)
    for section in selected_sections:
        parts.append(section.text)

    text, included = _join_with_char_limit(parts, max_chars, global_count=1 if parsed.global_text else 0)
    selected_count = max(0, included - (1 if parsed.global_text else 0))
    selected_headings = [section.heading for section in selected_sections[:selected_count]]
    return ExtendedContextSelection(
        text=text,
        selected_count=selected_count,
        total_sections=len(parsed.sections),
        selected_headings=selected_headings,
        used_fallback=False,
    )


# =============================================================================
# Markdown Cleanup Helpers
# =============================================================================

def _remove_reference_section(text):
    return re.sub(
        r"(?ms)^##\s+Reference Section Format\s*$.*?(?=^##\s+Supported Transferable Language\s*$)",
        "",
        text,
    )


# =============================================================================
# Section Scoring Helpers
# =============================================================================

def _section_score(section, query_tokens, query_text):
    heading_tokens = _tokens(section.heading)
    supported_tokens = _tokens(_supported_language_text(section.text))
    body_tokens = _tokens(section.text)
    score = 0
    score += 4 * len(query_tokens & heading_tokens)
    score += 2 * len(query_tokens & supported_tokens)
    score += len(query_tokens & body_tokens)
    score += _phrase_bonus(section.text, query_text)
    return score


def _supported_language_text(section_text):
    match = re.search(
        r"(?is)\*\*Supported transferable language:\*\*(.*?)(?=\n\*\*|^###|\Z)",
        section_text,
    )
    return match.group(1) if match else ""


def _tokens(text):
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9&+/#.-]{2,}", (text or "").lower())
        if token not in _STOP_WORDS
    }


def _phrase_bonus(section_text, query_text):
    section_lower = (section_text or "").lower()
    query_words = [
        word for word in re.findall(r"[a-z0-9][a-z0-9&+/#.-]{2,}", (query_text or "").lower())
        if word not in _STOP_WORDS
    ]
    bonus = 0
    seen = set()
    for size in (4, 3, 2):
        for idx in range(0, max(0, len(query_words) - size + 1)):
            phrase = " ".join(query_words[idx:idx + size])
            if phrase in seen:
                continue
            seen.add(phrase)
            if phrase in section_lower:
                bonus += size
    return bonus


# =============================================================================
# Text Assembly Helpers
# =============================================================================

def _join_with_char_limit(parts, max_chars, *, global_count=0):
    included_parts = []
    included = 0
    for part in parts:
        candidate = "\n\n".join(included_parts + [part]).strip()
        if len(candidate) <= max_chars:
            included_parts.append(part)
            included += 1
            continue
        if not included_parts:
            return _cap_text(part, max_chars), 1
        if included <= global_count:
            remaining = max_chars - len("\n\n".join(included_parts)) - 2
            if remaining > 100:
                included_parts.append(_cap_text(part, remaining))
                included += 1
        break
    return "\n\n".join(included_parts).strip(), included


def _cap_text(text, max_chars):
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


# =============================================================================
# Config Helpers
# =============================================================================

def _setting(name, default):
    value = getattr(config, name, None)
    return default if value in (None, "") else value


def _int_setting(name, default, *, minimum):
    try:
        value = int(_setting(name, default))
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _bool_setting(name, default):
    value = _setting(name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


# =============================================================================
# Token Filtering
# =============================================================================

_STOP_WORDS = {
    "and", "the", "for", "with", "from", "that", "this", "into", "role",
    "roles", "source", "basis", "safe", "usage", "boundaries", "claim",
    "direct", "unless", "resume", "extended", "supported", "transferable",
    "language", "analysis", "analyst",
}
