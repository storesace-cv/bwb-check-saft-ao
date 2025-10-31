"""Utilities to repair ``WorkDocument`` tag balancing issues."""

from __future__ import annotations

import re
from pathlib import Path

_ENCODING_DECLARATION = re.compile(
    r"(<\?xml\\b[^>]*\\bencoding\\s*=\\s*)([\"\'])([^\"\']*)(\2)",
    re.IGNORECASE,
)

_WORK_DOCUMENT_TAG = re.compile(r"<(/?)WorkDocument\b[^>]*>")


def repair_workdocument_balance(text: str) -> tuple[str, bool]:
    """Return ``text`` ensuring ``WorkDocument`` tags are properly balanced.

    The routine walks through the ``WorkDocument`` opening and closing tags
    maintaining a stack with the indentation detected for each opening tag.
    When a duplicate closing tag is found (i.e. without a corresponding
    opening tag on the stack) it is removed.  Conversely, when a new opening
    tag is encountered while a previous one is still open, a closing tag is
    injected before continuing.  Any remaining open tags at the end of the
    traversal are closed in the order they were opened.

    Parameters
    ----------
    text:
        The original XML text.

    Returns
    -------
    tuple[str, bool]
        The potentially modified XML text and a boolean indicating whether
        modifications were applied.
    """

    stack: list[str] = []
    output: list[str] = []
    last_end = 0
    changed = False

    for match in _WORK_DOCUMENT_TAG.finditer(text):
        start, end = match.span()
        output.append(text[last_end:start])

        indent = _detect_indent(text, start)
        tag_text = match.group(0)
        is_closing = match.group(1) == "/"

        if is_closing:
            if stack:
                stack.pop()
                output.append(tag_text)
            else:
                # Duplicate closing tag – drop it.
                changed = True
        else:
            if stack:
                # Close any previously open WorkDocument blocks before
                # starting a new one.
                while stack:
                    prev_indent = stack.pop()
                    output.append(f"</WorkDocument>\n{prev_indent}")
                    changed = True
            stack.append(indent)
            output.append(tag_text)

        last_end = end

    tail = text[last_end:]
    if stack:
        changed = True
        closing_parts = []
        while stack:
            prev_indent = stack.pop()
            closing_parts.append(f"</WorkDocument>\n{prev_indent}")
        tail = "".join(closing_parts) + tail

    output.append(tail)
    fixed = "".join(output)
    return fixed, changed


def repair_workdocument_balance_in_file(path: Path) -> bool:
    """Repair ``WorkDocument`` tag balance issues directly in ``path``.

    Returns ``True`` when modifications were required and applied.
    """

    original, encoding = _read_text_with_fallback(path)
    fixed, changed = repair_workdocument_balance(original)
    if changed:
        if encoding.lower() != "utf-8":
            fixed = _ensure_utf8_encoding_declaration(fixed)
        path.write_text(fixed, encoding="utf-8")
    return changed


def _detect_indent(text: str, pos: int) -> str:
    """Return the whitespace indentation for the line preceding ``pos``."""

    line_start = text.rfind("\n", 0, pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1
    indent = text[line_start:pos]
    if indent.strip():
        return ""
    return indent


def _read_text_with_fallback(path: Path) -> tuple[str, str]:
    """Return the text for ``path`` using UTF-8 with legacy fallbacks."""

    data = path.read_bytes()
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        for encoding in ("cp1252", "latin-1"):
            try:
                return data.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
    return data.decode("utf-8", errors="replace"), "utf-8"


def _ensure_utf8_encoding_declaration(text: str) -> str:
    """Normalise the XML declaration to advertise UTF-8 output."""

    def _replace(match: re.Match[str]) -> str:
        prefix, quote = match.group(1), match.group(2)
        return f"{prefix}{quote}UTF-8{quote}"

    updated, count = _ENCODING_DECLARATION.subn(_replace, text, count=1)
    if count:
        return updated

    stripped = text.lstrip()
    if stripped.startswith("<?xml"):
        offset = text.index(stripped)
        end_decl = stripped.find("?>")
        if end_decl != -1:
            insertion = ' encoding="UTF-8"'
            absolute_end = offset + end_decl
            return text[:absolute_end] + insertion + text[absolute_end:]

    return text

