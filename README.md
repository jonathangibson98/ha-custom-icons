# Auto Icons

Install: copy `custom_components/auto_icons` into `/config/custom_components/`, restart HA,
then Settings > Devices & services > Add integration > Auto Icons.

Pick a folder name (created under /config). Drop .svg files in it. Use them anywhere as
`prefix:filename` (no .svg), e.g. `my_icons:garage-door`. Subfolders work: `my_icons:rooms/kitchen`.
Add the integration again to make more folders, each with its own prefix.
