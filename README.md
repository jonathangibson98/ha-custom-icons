<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="custom_components/auto_custom_icons/brand/dark_logo@2x.png">
    <img src="custom_components/auto_custom_icons/brand/logo@2x.png" alt="Auto Custom Icons" width="520">
  </picture>
</p>

<p align="center">
  <a href="https://github.com/hacs/integration"><img alt="HACS Custom" src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <a href="https://github.com/jonathangibson98/ha-custom-icons/actions/workflows/hassfest.yaml"><img alt="Hassfest" src="https://github.com/jonathangibson98/ha-custom-icons/actions/workflows/hassfest.yaml/badge.svg"></a>
</p>

# Auto Custom Icons

Make a folder, drop SVG files in it, and use them anywhere in Home Assistant as
`yourprefix:filename`. **No reload button, no restart, no browser refresh.** New and edited
icons show up on their own within a few seconds.

You choose the folder name when you add the integration. Add it again to make more folders.

- [Features](#features)
- [Requirements](#requirements)
- [Install](#install)
- [Setup](#setup)
- [Using your icons](#using-your-icons)
- [Adding, editing and deleting icons](#adding-editing-and-deleting-icons)
- [Making SVGs that look right](#making-svgs-that-look-right)
- [How it works](#how-it-works)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Uninstall](#uninstall)
- [Development](#development)
- [Credits](#credits) / [License](#license)

## Features

- **You pick the folder.** Entered in the Add Integration dialog, created for you inside `/config`.
- **Live updates.** The folder is watched; add, change, or delete an SVG and open dashboards
  update without a manual reload.
- **Multiple folders.** Each folder gets its own prefix, so `kitchen:` and `garage:` can be separate.
- **Subfolders.** `my_icons/rooms/kitchen.svg` is used as `my_icons:rooms/kitchen`.
- **Colors work.** Multi-color and multi-shape SVGs render as drawn, not flattened to one path.
- **Works in the apps.** Browser, iOS Companion app, Android Companion app.
- **No dependencies, no build step.** Plain Python and plain JavaScript.

## Requirements

- Home Assistant **2024.7.0 or newer** (uses the static path API).
- Home Assistant **2026.3 or newer** to see the integration's logo and icon in the UI. On older
  versions everything works, you just get the default placeholder image.
- Access to your `/config` folder (File editor add-on, Samba, SSH, VS Code add-on, etc.) to
  drop SVG files in.

## Install

### HACS (custom repository)

1. HACS > three-dot menu > **Custom repositories**.
2. Repository: `https://github.com/jonathangibson98/ha-custom-icons`, Type: **Integration**.
3. Find **Auto Custom Icons** in HACS, click **Download**.
4. **Restart Home Assistant.**

### Manual

1. Copy the `custom_components/auto_custom_icons` folder from this repo into
   `/config/custom_components/` so you end up with
   `/config/custom_components/auto_custom_icons/manifest.json`.
2. **Restart Home Assistant.**

> The folder name must be exactly `auto_custom_icons`. Home Assistant will not load an
> integration whose folder name does not match its domain.

## Setup

1. **Settings > Devices & services > Add integration** and search for **Auto Custom Icons**.
2. Fill in the two fields:
   - **Folder name**: what the folder is called, e.g. `my_icons`. This creates
     `/config/my_icons`. Letters, numbers, `_` and `-` only.
   - **Icon prefix** (optional): what you type before the colon. Leave it blank to use the
     folder name. Lowercase letters, numbers, `_` and `-` only.
3. Submit. The folder now exists.
4. **Do one hard refresh of your browser once** (or fully close and reopen the Companion app).
   The integration injects a small script into the frontend, and open pages only pick that up
   on load. You only ever do this once after installing. Adding more folders later needs no refresh.

Want another folder (for example one for a specific dashboard)? Add the integration again with a
different folder name and prefix.

Some names are off limits because Home Assistant or other icon packs use them, such as folders
like `www` and `custom_components`, and prefixes like `mdi`, `hass`, `fas`, `far`, `fab`.
The form tells you if you hit one.

## Using your icons

Say your prefix is `my_icons` and you saved `/config/my_icons/garage-door.svg`. The icon is
`my_icons:garage-door` (no `.svg`).

**Entity icon in the UI**: Settings > Devices & services > Entities > pick an entity > Settings
(gear) > **Icon**, and type `my_icons:garage-door`.

**Dashboard card:**

```yaml
type: tile
entity: cover.garage_door
icon: my_icons:garage-door
```

**Button card, entities card, etc.:**

```yaml
type: button
name: Garage
icon: my_icons:garage-door
tap_action:
  action: toggle
entity: cover.garage_door
```

**Customize in YAML:**

```yaml
homeassistant:
  customize:
    cover.garage_door:
      icon: my_icons:garage-door
```

**Template / helper / group icon:**

```yaml
template:
  - sensor:
      - name: Garage state
        state: "{{ states('cover.garage_door') }}"
        icon: >
          {{ 'my_icons:garage-open' if is_state('cover.garage_door', 'open')
             else 'my_icons:garage-closed' }}
```

**Subfolders:** `/config/my_icons/rooms/kitchen.svg` is `my_icons:rooms/kitchen`.

Naming tip: stick to lowercase letters, numbers, `-`, `_` and `/` in file names. Avoid spaces
and colons.

## Adding, editing and deleting icons

| You do this | What happens |
| --- | --- |
| Drop a new `.svg` in the folder | Usable within about 3 seconds. Any card already showing that name (because you typed it in before the file existed) fills in by itself. |
| Overwrite or edit an existing `.svg` | Icons on screen refresh by themselves within a few seconds. |
| Delete an `.svg` | The icon goes blank on screen within a few seconds. |
| Add the integration again (new folder) | The new prefix works immediately, no refresh. |
| Remove the integration | The prefix stops working immediately. Your files are **not** deleted. |

The folder is checked every 3 seconds. Only `.svg` files are looked at, and anything in a folder
whose name starts with `.` is ignored.

## Making SVGs that look right

- **Include a `viewBox`**, e.g. `viewBox="0 0 24 24"`. Without one, the width and height
  attributes are used, and if those are missing too it assumes 24x24.
- **Want the icon to take your theme color?** Use `fill="currentColor"` (or leave fill off), and
  remove hard-coded colors. The icon will then match its card the same way built-in icons do.
- **Want fixed colors?** Leave your colors in. They are kept exactly as drawn.
- Keep files small. Anything over 1 MB is ignored.
- Export as plain SVG. "Optimized"/minified SVGs from tools like SVGO work fine.

## How it works

- **Backend** (`__init__.py`, `icons.py`): each folder you add is watched by a small poller. The
  frontend asks Home Assistant over the existing websocket for a list of prefixes, a list of
  icons, or one icon. Icons are read from disk when requested, so there is no server-side cache
  to go stale.
- **Frontend** (`loader.js`): registers each prefix with Home Assistant's custom icon API
  (`window.customIcons`), keeps a small in-browser cache, and subscribes to a "folder changed"
  push from the server. When something changes it clears the cache and re-renders any icons
  currently on screen.
- **Multi-color rendering**: Home Assistant's own icon element only draws a single path, so
  the loader patches `ha-icon` slightly so it can draw the whole SVG body.

There is no YAML configuration and no config options page: everything is the Add Integration form.

## Security

Icons are drawn by inserting the SVG's contents into the page (that is what makes colors and
multi-shape icons work). Because of that:

- Only put SVG files in these folders that you trust. Anyone who can write to the folder can
  influence what is drawn on your dashboards.
- As a safety net, the integration strips `<script>` tags, `<foreignObject>` blocks, `on...=`
  event attributes and `javascript:` links from every icon before sending it to the browser.
  This is basic filtering, not a guarantee against a malicious file.
- File access is locked to the folder you chose. Names containing `../` and symlinks that point
  outside the folder are refused.
- Any logged-in user can request icons (so they work for non-admin dashboards), but only the
  names and drawing data of files in your icon folders are exposed.

## Troubleshooting

**The integration does not show up in Add Integration.**
Confirm the folder is `/config/custom_components/auto_custom_icons/` and contains
`manifest.json`, then restart Home Assistant fully (not just reload YAML). Check
Settings > System > Logs for errors mentioning `auto_custom_icons`.

**My icon shows as blank.**
Work through these in order:
1. Is the prefix right? Settings > Devices & services > Auto Custom Icons shows it in the entry title.
2. Is the file name right? `garage-door.svg` is used as `my_icons:garage-door` (no `.svg`,
   case sensitive on Linux).
3. Open the file in a text editor. It must start with `<svg` and end with `</svg>`.
4. Wait a few seconds after saving, then check again.
5. Do the one-time hard refresh from [Setup](#setup) if you have not yet.

**It works in the browser but not in the phone app.**
Fully close the Companion app (swipe it away) and reopen it. The app caches the page script
more aggressively than a browser.

**The icon draws but the wrong color.**
Your SVG has a hard-coded fill. Replace it with `fill="currentColor"` to follow the theme.

**The integration logo is a gray placeholder.**
Brand images from the integration folder need Home Assistant 2026.3 or newer. Home Assistant
also caches brand images, so after updating restart it and hard refresh the browser.

**Still stuck?**
Open an issue with your Home Assistant version, the icon name you used, and the SVG file if
you can. The bug report form lists what to include. In the browser, open the developer console
and look for lines starting with `[auto_custom_icons]`.

## Uninstall

1. Settings > Devices & services > Auto Custom Icons > three-dot menu > **Delete** (do this for
   each folder you added).
2. Remove it in HACS, or delete `/config/custom_components/auto_custom_icons`.
3. Restart Home Assistant.

Your icon folders (for example `/config/my_icons`) are left alone. Delete them yourself if you
no longer want the files.

## Development

The SVG and folder-scanning logic in `icons.py` has no Home Assistant imports so it can be tested
on its own:

```bash
pip install pytest
pytest -q tests
```

Repo layout:

```
custom_components/auto_custom_icons/
  __init__.py      setup, folder watcher, websocket API
  config_flow.py   the Add Integration form + validation
  icons.py         folder scanning, SVG parsing + sanitising
  loader.js        frontend: registers prefixes, caches, live refresh
  const.py
  manifest.json
  translations/en.json
  brand/           icon.png, logo.png (+ @2x and dark variants) for HA 2026.3+
tests/             unit tests for icons.py
.github/workflows/ hassfest, HACS validation, tests
```

Changes are listed in [CHANGELOG.md](CHANGELOG.md).

## Credits

Inspired by [thomasloven/hass-custom_icons](https://github.com/thomasloven/hass-custom_icons)
(MIT), which pioneered the `window.customIcons` approach this builds on. This project is a
separate, much smaller implementation focused on one thing: your own SVGs, in a folder you
name, loading automatically.

## License

[MIT](LICENSE)
