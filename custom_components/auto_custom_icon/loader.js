// Auto Icons frontend loader. Plain JS, no build step.
//  - registers each configured prefix with HA's window.customIcons
//  - fetches icons over the websocket (cached in the browser)
//  - server pushes "folder changed" events, so new/edited icons show up live

const DOMAIN = "auto_icons";
const SVG_NS = "http://www.w3.org/2000/svg";
const MISSING_RETRY_MS = 5000;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let _conn;
async function getConnection() {
  if (_conn) return _conn;
  await Promise.race([
    customElements.whenDefined("home-assistant"),
    customElements.whenDefined("hc-main"),
  ]);
  const tag = customElements.get("home-assistant") ? "home-assistant" : "hc-main";
  while (!document.querySelector(tag)) await sleep(100);
  const el = document.querySelector(tag);
  while (!el.hass) await sleep(100);
  _conn = el.hass.connection;
  return _conn;
}

// ------------------------------------------------------------------ icon cache

const registered = new Set();
const cache = {}; // prefix -> Map(name -> {promise, missing, t})

const emptyIcon = () => ({ path: "", viewBox: "0 0 24 24", missing: true });

function toCustomIcon(d) {
  const vb = Array.isArray(d.viewBox) ? d.viewBox.join(" ") : "0 0 24 24";
  return {
    path: d.path || "",
    secondaryPath: d.path2 || "",
    viewBox: vb,
    format: "custom_icons",
    innerSVG: d.body || "",
    attributes: { height: "1em", width: "1em", viewBox: vb },
  };
}

function getIcon(prefix, name) {
  const store = (cache[prefix] ??= new Map());
  const hit = store.get(name);
  if (hit && (!hit.missing || Date.now() - hit.t < MISSING_RETRY_MS)) return hit.promise;

  const entry = { missing: false, t: Date.now() };
  entry.promise = (async () => {
    try {
      const conn = await getConnection();
      const data = await conn.sendMessagePromise({ type: `${DOMAIN}/icon`, prefix, icon: name });
      return data ? toCustomIcon(data) : emptyIcon();
    } catch (err) {
      return emptyIcon();
    }
  })().then((icon) => {
    if (icon.missing) entry.missing = true;
    return icon;
  });
  store.set(name, entry);
  return entry.promise;
}

async function getIconList(prefix) {
  const conn = await getConnection();
  return conn.sendMessagePromise({ type: `${DOMAIN}/list`, prefix });
}

// ------------------------------------------------- live <ha-icon> bookkeeping

const seen = new WeakSet();
const live = new Set(); // WeakRef<ha-icon>

function trackIcon(el) {
  if (seen.has(el)) return;
  const p = typeof el.icon === "string" ? el.icon.split(":")[0] : "";
  if (!p || p === "mdi") return;
  seen.add(el);
  live.add(new WeakRef(el));
}

// Re-render icons currently on screen. prefix=null means "all tracked icons".
function refreshLive(prefix) {
  for (const ref of [...live]) {
    const el = ref.deref();
    if (!el || !el.isConnected) {
      live.delete(ref);
      continue;
    }
    if (typeof el.icon !== "string") continue;
    if (prefix && el.icon.split(":")[0] !== prefix) continue;
    try {
      el._legacy = false;
      el._loadIcon();
    } catch (err) {
      /* ignore */
    }
  }
}

// --------------------------------------------------------- prefix registration

function register(prefix) {
  window.customIcons[prefix] = {
    getIcon: (name) => getIcon(prefix, name),
    getIconList: () => getIconList(prefix),
  };
  registered.add(prefix);
}

async function refreshPrefixes() {
  const conn = await getConnection();
  const prefixes = await conn.sendMessagePromise({ type: `${DOMAIN}/prefixes` });
  for (const p of prefixes) if (!registered.has(p)) register(p);
  for (const p of [...registered]) {
    if (!prefixes.includes(p)) {
      delete window.customIcons[p];
      registered.delete(p);
      delete cache[p];
    }
  }
  refreshLive(null);
}

function onServerEvent(ev) {
  if (ev.kind === "entries") {
    refreshPrefixes();
  } else {
    delete cache[ev.prefix];
    refreshLive(ev.prefix);
  }
}

// ----------------------------------------------------- patch <ha-icon> for SVG

customElements.whenDefined("ha-icon").then(() => {
  const proto = customElements.get("ha-icon").prototype;

  // Draw the full SVG body (colours, multiple shapes) instead of one path.
  const origSetCustomPath = proto._setCustomPath;
  proto._setCustomPath = async function (promise, requestedIcon) {
    if (origSetCustomPath) await origSetCustomPath.call(this, promise, requestedIcon);
    const icon = await promise;
    if (requestedIcon !== this.icon) return;
    if (!icon || !icon.innerSVG || icon.format !== "custom_icons") return;

    await this.updateComplete;
    const svgIcon = this.shadowRoot?.querySelector("ha-svg-icon");
    await svgIcon?.updateComplete;
    const svg = svgIcon?.shadowRoot?.querySelector("svg");
    if (!svg) return;

    this._path = undefined;
    this._secondaryPath = undefined;
    let g = svg.querySelector(".customIcon");
    if (!g) {
      g = document.createElementNS(SVG_NS, "g");
      g.setAttribute("class", "customIcon");
      svg.appendChild(g);
    }
    g.innerHTML = icon.innerSVG;
  };

  // Track icons so we can refresh them live, and clean up when an element
  // switches from one of our icons to something else.
  const origLoadIcon = proto._loadIcon;
  proto._loadIcon = async function () {
    trackIcon(this);
    if (origLoadIcon) await origLoadIcon.call(this);
    const prefix = typeof this.icon === "string" ? this.icon.split(":")[0] : null;
    if (!registered.has(prefix)) {
      this.updateComplete.then(async () => {
        const svgIcon = this.shadowRoot?.querySelector("ha-svg-icon");
        await svgIcon?.updateComplete;
        svgIcon?.shadowRoot?.querySelector(".customIcon")?.remove();
      });
    }
  };
});

// ------------------------------------------------------------------------ boot

(async () => {
  if (!("customIcons" in window)) window.customIcons = {};
  try {
    const conn = await getConnection();
    await refreshPrefixes();
    await conn.subscribeMessage(onServerEvent, { type: `${DOMAIN}/subscribe` });
    conn.addEventListener?.("ready", () => {
      for (const k of Object.keys(cache)) delete cache[k];
      refreshPrefixes();
    });
  } catch (err) {
    console.warn("[auto_icons] could not start:", err);
  }
})();
