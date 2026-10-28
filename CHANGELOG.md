# Changelog

## 1.0.0 - 2026-10-28

First release.

- Pick your own folder name when adding the integration; it is created inside `/config`.
- Drop `.svg` files in the folder and use them as `prefix:filename`. No reload button.
- New, edited, and deleted icons are picked up within a few seconds and pushed to open
  dashboards live (no browser refresh).
- Multiple folders supported (add the integration again), each with its own prefix.
- Subfolders supported (`prefix:rooms/kitchen`).
- Multi-color and multi-shape SVGs render correctly.
- Basic SVG sanitising (scripts, event handlers, `javascript:` links removed).
- Brand icon and logo (light and dark) shipped in `brand/` for Home Assistant 2026.3+.
