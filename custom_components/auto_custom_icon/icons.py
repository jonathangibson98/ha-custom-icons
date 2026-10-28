"""Filesystem + SVG helpers. No Home Assistant imports, so this stays testable."""
from __future__ import annotations

import os
import re

MAX_BYTES = 1_000_000

_NUM = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_SVG_OPEN = re.compile(r"<svg\b([^>]*)>", re.I | re.S)
_PATH_TAG = re.compile(r"<path\b[^>]*>", re.I | re.S)

# Basic sanitising. The icon body is injected with innerHTML so colours and
# multi-shape SVGs work, which means we strip the obviously dangerous stuff.
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_SCRIPT = re.compile(r"<script\b.*?</script\s*>|<script\b[^>]*/>", re.I | re.S)
_FOREIGN = re.compile(r"<foreignObject\b.*?</foreignObject\s*>", re.I | re.S)
_ON_ATTR = re.compile(r"""\son[a-z]+\s*=\s*(?:"[^"]*"|'[^']*')""", re.I)
_JS_HREF = re.compile(r"""((?:xlink:)?href\s*=\s*["'])\s*javascript:[^"']*""", re.I)


def scan(root: str) -> dict[str, tuple[int, int]]:
    """Return {icon_name: (mtime_ns, size)} for every .svg under root."""
    found: dict[str, tuple[int, int]] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.startswith(".") or not fn.endswith(".svg"):
                continue
            full = os.path.join(dirpath, fn)
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            found[rel[: -len(".svg")]] = (st.st_mtime_ns, st.st_size)
    return found


def list_icons(root: str) -> list[str]:
    return sorted(scan(root))


def read_icon(root: str, name: str) -> dict | None:
    """Read + process one icon. Returns None if missing/unsafe/unparseable."""
    root_real = os.path.realpath(root)
    full = os.path.realpath(os.path.join(root_real, name + ".svg"))
    # Block ../ tricks and symlinks that point outside the folder.
    if not full.startswith(root_real + os.sep):
        return None
    try:
        if os.path.getsize(full) > MAX_BYTES:
            return None
        with open(full, encoding="utf-8", errors="replace") as fp:
            text = fp.read()
    except OSError:
        return None
    return process_svg(text)


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(
        r"(?:^|\s)" + re.escape(name) + r"""\s*=\s*(?:"([^"]*)"|'([^']*)')""",
        attrs,
        re.I | re.S,
    )
    if not m:
        return None
    return m.group(1) if m.group(1) is not None else m.group(2)


def _fmt(n: float) -> int | float:
    return int(n) if n == int(n) else n


def _viewbox(attrs: str) -> list:
    vb = _attr(attrs, "viewBox")
    if vb:
        nums = [float(x) for x in _NUM.findall(vb)]
        if len(nums) == 4 and nums[2] > 0 and nums[3] > 0:
            return [_fmt(n) for n in nums]
    w, h = _attr(attrs, "width"), _attr(attrs, "height")
    if w and h and "%" not in w and "%" not in h:
        wn, hn = _NUM.findall(w), _NUM.findall(h)
        if wn and hn and float(wn[0]) > 0 and float(hn[0]) > 0:
            return [0, 0, _fmt(float(wn[0])), _fmt(float(hn[0]))]
    return [0, 0, 24, 24]


def process_svg(text: str) -> dict | None:
    text = text.lstrip("\ufeff")
    m = _SVG_OPEN.search(text)
    end = text.lower().rfind("</svg>")
    if not m or end == -1 or end < m.end():
        return None

    attrs = m.group(1)
    body = text[m.end() : end]
    body = _COMMENT.sub("", body)
    body = _SCRIPT.sub("", body)
    body = _FOREIGN.sub("", body)
    body = _ON_ATTR.sub("", body)
    body = _JS_HREF.sub(r"\1#", body)

    ds = []
    for tag in _PATH_TAG.findall(body):
        d = _attr(tag, "d")
        if d:
            ds.append(d)

    return {
        "viewBox": _viewbox(attrs),
        "path": " ".join(ds),
        "path2": "",
        "body": body.strip(),
    }
