"""Tests for the SVG/filesystem helpers. They load icons.py directly so Home Assistant
is not required to run them."""
import importlib.util
import os
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "icons",
    Path(__file__).parent.parent / "custom_components" / "auto_custom_icons" / "icons.py",
)
icons = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(icons)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_simple_icon(tmp_path):
    _write(tmp_path / "a.svg", '<svg viewBox="0 0 24 24"><path d="M1 1h22v22H1z"/></svg>')
    data = icons.read_icon(str(tmp_path), "a")
    assert data["viewBox"] == [0, 0, 24, 24]
    assert data["path"] == "M1 1h22v22H1z"


def test_viewbox_falls_back_to_width_height_then_default(tmp_path):
    _write(tmp_path / "w.svg", '<svg width="48" height="32"><circle r="1"/></svg>')
    _write(tmp_path / "n.svg", "<svg><circle r='1'/></svg>")
    assert icons.read_icon(str(tmp_path), "w")["viewBox"] == [0, 0, 48, 32]
    assert icons.read_icon(str(tmp_path), "n")["viewBox"] == [0, 0, 24, 24]


def test_sanitises_dangerous_content(tmp_path):
    _write(
        tmp_path / "x.svg",
        '<svg viewBox="0 0 10 10"><circle onclick="alert(1)" r="2" fill="#f00"/>'
        "<script>alert(1)</script>"
        '<a xlink:href="javascript:alert(1)"><path d="M0 0"/></a>'
        "<foreignObject><div>hi</div></foreignObject></svg>",
    )
    body = icons.read_icon(str(tmp_path), "x")["body"].lower()
    for bad in ("onclick", "<script", "javascript", "foreignobject"):
        assert bad not in body
    assert 'fill="#f00"' in body  # colours are kept


def test_rejects_garbage_and_missing(tmp_path):
    _write(tmp_path / "bad.svg", "not an svg")
    assert icons.read_icon(str(tmp_path), "bad") is None
    assert icons.read_icon(str(tmp_path), "nope") is None


def test_blocks_path_traversal(tmp_path):
    root = tmp_path / "icons"
    _write(root / "ok.svg", "<svg><path d='M0 0'/></svg>")
    _write(tmp_path / "secret.svg", "<svg><path d='M9 9'/></svg>")
    assert icons.read_icon(str(root), "../secret") is None
    assert icons.read_icon(str(root), "sub/../../secret") is None


def test_symlink_escape_blocked(tmp_path):
    root = tmp_path / "icons"
    root.mkdir()
    _write(tmp_path / "outside.svg", "<svg><path d='M9 9'/></svg>")
    try:
        os.symlink(tmp_path / "outside.svg", root / "link.svg")
    except OSError:
        return  # symlinks unavailable on this platform
    assert icons.read_icon(str(root), "link") is None


def test_scan_lists_nested_and_skips_hidden(tmp_path):
    _write(tmp_path / "a.svg", "<svg/>")
    _write(tmp_path / "rooms" / "kitchen.svg", "<svg/>")
    _write(tmp_path / ".hidden" / "x.svg", "<svg/>")
    _write(tmp_path / "notes.txt", "x")
    assert icons.list_icons(str(tmp_path)) == ["a", "rooms/kitchen"]


def test_scan_detects_add_edit_delete(tmp_path):
    first = icons.scan(str(tmp_path))
    _write(tmp_path / "n.svg", "<svg><path d='M0 0'/></svg>")
    added = icons.scan(str(tmp_path))
    assert added != first
    time.sleep(0.02)
    _write(tmp_path / "n.svg", "<svg><path d='M0 0L1 1L2 2'/></svg>")
    edited = icons.scan(str(tmp_path))
    assert edited != added
    (tmp_path / "n.svg").unlink()
    assert icons.scan(str(tmp_path)) != edited


def test_scan_missing_folder_is_empty():
    assert icons.scan("/definitely/not/here") == {}
