"""Utilities to repair ``WorkDocument`` tag balancing issues."""

from __future__ import annotations

import re
from pathlib import Path

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

    original = path.read_text(encoding="utf-8")
    fixed, changed = repair_workdocument_balance(original)
    if changed:
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

