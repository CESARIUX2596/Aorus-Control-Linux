'use strict';
const $ = id => document.getElementById(id);
const copy = v => structuredClone(v);
const BUILD = '1.2.1';
let state, config, currentName = 'Aurora', templateId = 'aurora', filter = 'All';
let painting = false, dirty = false, busy = false, previewSeq = 0, previewTimer, toastTimer;
let selectedTemplate, previousBrightness = 70;
let themeSearch = '';
const keyNodes = new Map();

function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('toast').textContent = message;
  $('toast').className = `toast${error ? ' error' : ''}`;
  toastTimer = setTimeout(() => $('toast').classList.add('hidden'), error ? 9000 : 5000);
}
async function api(path, data) {
  const response = await fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Lumen-Token': state.token}, body: JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || 'Could not complete this action.');
  return result;
}
function setBusy(value) {
  busy = value;
  for (const id of ['apply-once', 'apply-remember', 'startup-current', 'startup-toggle']) $(id).disabled = value;
  $('apply-remember').firstElementChild.textContent = value ? 'Setting the mood…' : 'Save to keyboard';
}
function showPage(page) {
  for (const el of document.querySelectorAll('.page')) el.classList.toggle('hidden', el.id !== `page-${page}`);
  for (const el of document.querySelectorAll('.nav-item')) el.classList.toggle('active', el.dataset.page === page);
  $('page-name').textContent = {studio: 'Keyboard studio', system: 'Laptop controls', library: 'My profiles', startup: 'Startup & restore'}[page];
  if (page === 'library') renderProfiles();
}
function temperature(value) { return Number.isFinite(value) ? `${Math.round(value)}°C` : '—'; }
function systemButton(container, label, name, value, disabled = false) {
  const button = document.createElement('button');
  button.className = 'button secondary'; button.textContent = label; button.disabled = disabled;
  button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      const result = await api('/api/system/action', {name, value});
      state.system = result.system; renderSystem(state.system); toast(`${label} applied.`);
    } catch (error) { toast(error.message, true); }
    finally { button.disabled = false; }
  });
  container.append(button);
}
function renderSystem(data) {
  if (!data) return;
  $('system-model').textContent = `${data.model || 'AORUS laptop'} · live readings update every 5 seconds`;
  const cpuUsage = data.cpu?.usage;
  $('cpu-usage').textContent = Number.isFinite(cpuUsage) ? `${cpuUsage}%` : '…';
  $('cpu-bar').style.width = `${Math.max(0, Math.min(100, cpuUsage || 0))}%`;
  $('cpu-temperature').textContent = `Peak CPU core · ${temperature(data.cpu?.temperature)}`;
  const gpuUsage = data.gpu?.utilization;
  $('gpu-usage').textContent = Number.isFinite(gpuUsage) ? `${gpuUsage}%` : '—';
  $('gpu-bar').style.width = `${Math.max(0, Math.min(100, gpuUsage || 0))}%`;
  const gpuParts = [];
  if (Number.isFinite(data.gpu?.temperature)) gpuParts.push(temperature(data.gpu.temperature));
  if (Number.isFinite(data.gpu?.power_watts)) gpuParts.push(`${Math.round(data.gpu.power_watts)} W`);
  $('gpu-detail').textContent = gpuParts.length ? `GPU temperature · ${gpuParts.join(' · ')}` : 'GPU telemetry unavailable';
  const fans = data.fans || [];
  $('fan-summary').textContent = fans.length ? `${fans.length} detected` : '—';
  $('fan-readings').textContent = fans.length ? fans.map(f => `${f.name} · ${f.rpm.toLocaleString()} RPM`).join(' / ') : 'Fan speed telemetry unavailable';
  $('fan-control-area').replaceChildren();
  if (data.fan_control?.available) {
    for (const mode of data.fan_control.modes) {
      if (mode.value === 5) continue;
      systemButton($('fan-control-area'), mode.name, 'fan-mode', String(mode.value), state.demo || mode.value === data.fan_control.current);
    }
    if (data.fan_control.speed_available) {
      const speedHint = document.createElement('p'); speedHint.className = 'help-text';
      speedHint.textContent = 'Fixed fan output · selecting a preset switches to fixed mode.';
      $('fan-control-area').append(speedHint);
      const speedChoices = document.createElement('div'); speedChoices.className = 'fan-speed-presets';
      for (const value of ['25', '50', '75', '100']) {
        const raw = Math.round(Number(value) * 255 / 100);
        systemButton(speedChoices, `${value}%`, 'fan-speed', value,
          state.demo || (data.fan_control.current === 5 && data.fan_control.custom_speed === raw));
      }
      $('fan-control-area').append(speedChoices);
    }
  } else {
    const hint = document.createElement('p'); hint.className = 'help-text';
    hint.textContent = data.fan_control?.reason || 'Fan mode control is unavailable.';
    $('fan-control-area').append(hint);
    const guide = document.createElement('a'); guide.className = 'system-driver-link';
    guide.href = 'https://github.com/tangalbert919/gigabyte-laptop-wmi/blob/master/USAGE.md';
    guide.target = '_blank'; guide.rel = 'noreferrer'; guide.textContent = 'Driver setup and supported controls ↗';
    $('fan-control-area').append(guide);
    if (!fans.length) {
      const hotkey = document.createElement('p'); hotkey.className = 'help-text';
      hotkey.textContent = 'Hardware shortcut: Fn + Esc requests maximum fan speed.';
      $('fan-control-area').append(hotkey);
    }
  }
  const battery = data.battery;
  $('battery-value').textContent = battery ? `${battery.percent}%` : '—';
  $('battery-bar').style.width = `${battery?.percent || 0}%`;
  $('battery-detail').textContent = battery ? battery.status : 'Battery status unavailable';
  $('charge-actions').replaceChildren();
  if (data.charging_limit?.available) {
    const limit = data.charging_limit;
    $('battery-detail').textContent += limit.enabled ? ` · charge cap ${limit.limit}%` : ' · charge cap off';
    systemButton($('charge-actions'), 'Default', 'charge-limit', 'default', state.demo || !limit.enabled);
    for (const value of ['60', '80', '100']) systemButton($('charge-actions'), `${value}% cap`, 'charge-limit', value, state.demo || (limit.enabled && String(limit.limit) === value));
  }
  $('profile-actions').replaceChildren();
  const profiles = data.power_profiles;
  $('profile-detail').textContent = profiles ? `Current · ${profiles.current || 'unknown'}` : 'Power profile service is not installed.';
  if (profiles) for (const profile of profiles.profiles) systemButton($('profile-actions'), profile.replace('-', ' '), 'power-profile', profile, state.demo || profile === profiles.current);
  $('wireless-actions').replaceChildren();
  const wireless = data.wireless || {};
  $('wireless-detail').textContent = `${wireless.wifi ? `Wi-Fi · ${wireless.wifi}` : 'Wi-Fi status unavailable'}${wireless.bluetooth_blocked === null ? '' : ` · Bluetooth · ${wireless.bluetooth_blocked ? 'off' : 'on'}`}`;
  if (wireless.wifi) systemButton($('wireless-actions'), wireless.wifi === 'enabled' ? 'Turn Wi-Fi off' : 'Turn Wi-Fi on', 'wifi', wireless.wifi === 'enabled' ? 'off' : 'on', state.demo);
  if (data.features?.bluetooth && wireless.bluetooth_blocked !== null) systemButton($('wireless-actions'), wireless.bluetooth_blocked ? 'Unblock Bluetooth' : 'Block Bluetooth', 'bluetooth', wireless.bluetooth_blocked ? 'on' : 'off', state.demo);
  $('audio-actions').replaceChildren();
  const audio = data.audio;
  $('audio-detail').textContent = audio ? `${audio.percent}%${audio.muted ? ' · muted' : ''}` : 'PipeWire volume control unavailable.';
  if (audio) {
    systemButton($('audio-actions'), '− Volume', 'volume', 'down', state.demo);
    systemButton($('audio-actions'), audio.muted ? 'Unmute' : 'Mute', 'volume', 'mute', state.demo);
    systemButton($('audio-actions'), '+ Volume', 'volume', 'up', state.demo);
  }
  const list = $('sensor-list'); list.replaceChildren();
  for (const item of (data.temperature_sensors || []).slice(0, 8)) {
    const row = document.createElement('div'); row.className = 'sensor-row';
    const label = document.createElement('span'); label.textContent = item.name;
    const value = document.createElement('strong'); value.textContent = temperature(item.celsius);
    row.append(label, value); list.append(row);
  }
  if (!list.childElementCount) list.textContent = 'No temperature sensors detected.';
  $('system-note').textContent = state.demo ? 'Preview mode: system controls are disabled.' : 'Fan mode controls appear when the Gigabyte WMI interface is installed and detected. System readings stay on this laptop.';
}
async function refreshSystem() {
  try {
    const response = await fetch('/api/system');
    if (response.ok) { state.system = await response.json(); renderSystem(state.system); }
  } catch { /* Keep the last local reading visible while the service reconnects. */ }
}
function markDirty() {
  dirty = true;
  $('applied-status').textContent = 'Preview · not applied';
  $('applied-status').classList.remove('applied');
}
function updateControls() {
  $('design-name').textContent = currentName;
  const theme = state.templates.find(t => t.id === templateId);
  $('design-description').textContent = theme ? theme.description : 'Your own palette. Your own atmosphere.';
  $('effect').value = config.effect;
  $('brightness').value = config.brightness;
  $('brightness-value').value = `${config.brightness}%`;
  $('brightness').style.setProperty('--range', `${config.brightness}%`);
  $('speed').value = config.speed;
  $('speed-value').value = `${config.speed} / 10`;
  $('speed').style.setProperty('--range', `${(config.speed - 1) / 9 * 100}%`);
  $('speed-control').classList.toggle('hidden', config.effect === 'custom' || config.effect === 'static');
  const gaming = config.effect === 'custom' && ['wasd', 'moba'].includes(config.pattern);
  const dimmed = config.effect === 'custom' && ['wasd', 'moba', 'scatter'].includes(config.pattern);
  $('background-control').classList.toggle('hidden', !dimmed);
  $('background').value = config.background ?? 8;
  $('background-value').value = `${config.background ?? 8}%`;
  $('background').style.setProperty('--range', `${(config.background ?? 8) / 40 * 100}%`);
  $('background-help').textContent = gaming ? 'Keep movement and action keys bright. Dim everything else; 0% turns the background off.' : 'Dim the background to bring the scattered lights into focus.';
  $('reverse-colors').classList.toggle('hidden', config.effect !== 'custom' || ['solid', 'wasd', 'moba'].includes(config.pattern));
  $('pattern-control').classList.toggle('hidden', config.effect !== 'custom');
  $('paint-section').classList.toggle('hidden', config.effect !== 'custom');
  $('palette-note').classList.toggle('hidden', config.effect === 'custom');
  $('effect-help').textContent = config.effect === 'custom' ? 'Choose your own colors for every key.' : config.effect === 'static' ? 'A steady glow in a built-in keyboard color.' : 'An onboard animation. Keeps running when you close this window.';
  for (let i = 0; i < 3; i++) {
    $(`color-${i}`).value = config.colors[i];
    $(`hex-${i}`).textContent = config.colors[i].toUpperCase();
    $(`color-${i}`).parentElement.querySelector('span').textContent = gaming ? ['BASE', config.pattern === 'moba' ? 'SPELL' : 'MOVE', 'ACT'][i] : `0${i+1}`;
    $(`color-${i}`).parentElement.style.opacity = config.effect !== 'custom' && i > 0 ? '.35' : '1';
    $(`color-${i}`).disabled = config.effect !== 'custom' && i > 0;
  }
  for (const el of document.querySelectorAll('[data-pattern]')) el.classList.toggle('active', el.dataset.pattern === config.pattern);
  $('power-button').lastElementChild.textContent = config.brightness ? 'Lights off' : 'Lights on';
  $('keyboard').style.setProperty('--light-opacity', .15 + config.brightness / 100 * .85);
  document.documentElement.style.setProperty('--color-a', config.colors[0]);
  document.documentElement.style.setProperty('--color-c', config.colors[2]);
  $('keyboard').className = `keyboard${painting ? ' painting' : ''} animated-${config.effect}`;
  $('preview-caption').textContent = config.effect === 'custom' ? 'Custom colors · onboard lighting' : `${state.effects[config.effect].label} · animation preview`;
  $('paint-toggle').classList.toggle('active', painting);
  $('paint-toggle').textContent = painting ? '✓ Brush enabled' : '✎ Paint individual keys';
  const painted = Object.keys(config.overrides).length;
  $('paint-help').textContent = painted ? `${painted} key${painted === 1 ? '' : 's'} customized. Click more keys to paint.` : 'Enable the brush, then click a key in the preview.';
}
async function preview() {
  const seq = ++previewSeq;
  try {
    const result = await api('/api/preview', {config});
    if (seq !== previewSeq) return;
    result.colors.forEach((color, slot) => {
      const key = keyNodes.get(slot);
      if (key) {
        key.style.setProperty('--key-color', color);
        const channels = color.match(/[a-f\d]{2}/gi).map(v => parseInt(v, 16));
        key.style.setProperty('--legend-color', Math.max(...channels) < 30 ? '#647183' : color);
        key.classList.toggle('custom-painted', Object.hasOwn(config.overrides, String(slot)) && config.effect === 'custom');
      }
    });
  } catch (e) { toast(e.message, true); }
}
function changed() {
  markDirty(); updateControls();
  clearTimeout(previewTimer);
  previewTimer = setTimeout(preview, 70);
}
function buildKeyboard() {
  $('keyboard').replaceChildren();
  for (const row of state.layout) {
    const el = document.createElement('div'); el.className = 'keyboard-row';
    for (const key of row) {
      const button = document.createElement('button');
      button.className = 'key'; button.textContent = key.label;
      button.style.gridColumn = `${Math.round((key.x - key.width / 2) * 4) + 1} / span ${Math.round(key.width * 4)}`;
      button.style.gridRow = `${key.y + 1} / span ${key.height}`;
      button.dataset.key = key.id;
      button.style.setProperty('--key-slot', key.slot);
      button.setAttribute('aria-label', `Paint ${key.id === 'space' ? 'Space' : key.label} key`);
      button.title = `${key.id} · click with the brush enabled to paint`;
      button.addEventListener('click', () => {
        if (!painting || config.effect !== 'custom') return toast('Enable “Paint individual keys” to customize a key.');
        config.overrides[String(key.slot)] = $('brush-color').value;
        changed();
      });
      keyNodes.set(key.slot, button); el.append(button);
    }
    $('keyboard').append(el);
  }
}
function miniKeyboard(config, preview) {
  const art = document.createElement('div'); art.className = 'theme-art';
  art.style.setProperty('--c2', config.colors[1]);
  const mini = document.createElement('div'); mini.className = 'mini-keyboard';
  for (const keys of state.layout) {
    for (const definition of keys) {
      const key = document.createElement('span'); key.className = 'mini-key';
      key.style.setProperty('--mini-color', preview[definition.slot]);
      key.style.gridColumn = `${Math.round((definition.x - definition.width / 2) * 4) + 1} / span ${Math.round(definition.width * 4)}`;
      key.style.gridRow = `${definition.y + 1} / span ${definition.height}`;
      key.dataset.slot = definition.slot;
      mini.append(key);
    }
  }
  art.append(mini); return art;
}
function renderTemplates() {
  $('templates').replaceChildren();
  $('theme-count').textContent = `${state.templates.length} BUILT-IN THEMES`;
  for (const theme of state.templates) {
    if (filter !== 'All' && theme.tag !== filter) continue;
    if (themeSearch && !`${theme.name} ${theme.description} ${theme.tag}`.toLocaleLowerCase().includes(themeSearch)) continue;
    const card = document.createElement('button'); card.className = 'theme-card';
    card.classList.toggle('selected', theme.id === templateId);
    card.setAttribute('aria-pressed', String(theme.id === templateId));
    card.title = theme.description;
    card.append(miniKeyboard(theme.config, theme.preview));
    const body = document.createElement('div'); body.className = 'theme-body';
    const title = document.createElement('h3'); title.textContent = theme.name;
    const tag = document.createElement('p'); tag.textContent = theme.tag;
    body.append(title, tag); card.append(body);
    if (theme.id === templateId) { const mark = document.createElement('span'); mark.className = 'selected-mark'; mark.textContent = '✓'; card.append(mark); }
    card.addEventListener('click', () => selectDesign(theme.config, theme.name, theme.id));
    $('templates').append(card);
  }
  $('theme-empty').classList.toggle('hidden', $('templates').childElementCount !== 0);
}
function selectDesign(value, name, id = null) {
  config = copy(value); currentName = name; templateId = id;
  selectedTemplate = copy(value); painting = false;
  changed(); renderTemplates();
}
function renderProfiles() {
  $('profile-count').textContent = state.profiles.length;
  $('profiles-empty').classList.toggle('hidden', state.profiles.length > 0);
  $('profiles').replaceChildren();
  for (const profile of state.profiles) {
    const card = document.createElement('article'); card.className = 'panel profile-card';
    card.append(miniKeyboard(profile.config, profile.preview));
    const body = document.createElement('div'); body.className = 'profile-content';
    const title = document.createElement('h2'); title.textContent = profile.name;
    const desc = document.createElement('p'); desc.textContent = `${state.effects[profile.config.effect].label} · ${profile.config.brightness}% brightness`;
    const actions = document.createElement('div'); actions.className = 'profile-actions';
    const load = document.createElement('button'); load.className = 'button secondary'; load.textContent = 'Open in studio ↗';
    load.addEventListener('click', () => { selectDesign(profile.config, profile.name); showPage('studio'); });
    const remove = document.createElement('button'); remove.className = 'icon-text'; remove.textContent = 'Delete'; remove.setAttribute('aria-label', `Delete ${profile.name}`);
    remove.addEventListener('click', async () => {
      if (!confirm(`Delete “${profile.name}” from your library?`)) return;
      try { state.profiles = (await api('/api/profiles/delete', {id: profile.id})).profiles; renderProfiles(); toast('Profile deleted.'); }
      catch (e) { toast(e.message, true); }
    });
    actions.append(load, remove); body.append(title, desc, actions); card.append(body); $('profiles').append(card);
  }
}
function updateStartup() {
  $('startup-toggle').checked = state.startup.enabled;
  $('startup-name').textContent = state.startup.config ? `${state.startup.name}${state.startup.enabled ? ' · restores before sign-in' : ' · automatic restore paused'}` : 'Save a design to choose your startup lighting.';
}
function connection() {
  const device = state.device;
  const ok = !state.demo && device.accessible;
  $('device-status').textContent = state.demo ? 'Interface preview' : ok ? 'AORUS 15P · Connected' : device.connected ? 'Keyboard · access needed' : 'Keyboard not available';
  $('device-dot').style.background = ok ? 'var(--accent)' : '#eab66e';
  const message = state.demo ? 'Preview mode: explore the interface and save demo profiles. No keyboard lighting is changed.' : !device.connected ? 'The keyboard is not available. Start Lumen from your desktop session, or reconnect the supported keyboard.' : !device.accessible ? 'One-time device setup is needed. Run ./install.sh from the project folder to enable lighting access.' : !state.startup.installed ? 'Lighting is available. Run ./install.sh to enable boot restore and add the app shortcut.' : '';
  $('connection-banner').textContent = message;
  $('connection-banner').classList.toggle('hidden', !message);
}
async function apply(remember) {
  if (busy) return;
  const applying = copy(config);
  const applyingName = currentName;
  setBusy(true);
  try {
    const result = await api(remember ? '/api/save-to-keyboard' : '/api/apply', {config: applying, name: applyingName});
    if (JSON.stringify(config) === JSON.stringify(applying)) {
      dirty = false;
      $('applied-status').textContent = state.demo ? 'Preview mode' : result.remembered ? '✓ Applied & remembered' : '✓ Applied to keyboard';
      $('applied-status').classList.add('applied');
    } else { markDirty(); }
    if (result.startup) { state.startup = result.startup; updateStartup(); }
    toast(result.message, result.remembered === false);
  } catch (e) { toast(e.message, true); }
  finally { setBusy(false); }
}
function openSave() { $('profile-name').value = currentName; $('save-dialog').showModal(); $('profile-name').select(); }

function compatibleState(value) {
  if (value.version !== BUILD || !Array.isArray(value.layout) || value.layout.length !== 6) return false;
  const validLayout = value.layout.every((row, y) => Array.isArray(row) && row.every(key =>
    Number.isInteger(key.slot) && key.slot >= 0 && key.slot < 128 &&
    Number.isFinite(key.x) && key.x > 0 && key.x < 19 && key.y === y &&
    Number.isFinite(key.width) && key.width > 0 && [1, 2].includes(key.height)));
  return value.system && validLayout && Array.isArray(value.templates) && value.templates.every(t => Array.isArray(t.preview) && t.preview.length === 128) &&
    Array.isArray(value.profiles) && value.profiles.every(p => Array.isArray(p.preview) && p.preview.length === 128);
}

async function init() {
  try {
    const response = await fetch('/api/state');
    if (!response.ok) throw new Error('Could not connect to the local lighting service.');
    state = await response.json();
    if (!compatibleState(state)) {
      $('connection-banner').classList.remove('hidden');
      $('connection-banner').textContent = 'Lumen is finishing an update. Reconnecting to the current keyboard layout…';
      setTimeout(() => location.reload(), 1500);
      return;
    }
    config = copy(state.active || state.startup.config || state.default);
    const matchingTemplate = state.templates.find(t => JSON.stringify(t.config) === JSON.stringify(config));
    const matchingProfile = state.profiles.find(p => JSON.stringify(p.config) === JSON.stringify(config));
    currentName = state.active ? (matchingProfile?.name || matchingTemplate?.name || 'Custom lighting') : state.startup.config ? state.startup.name : 'Aurora';
    templateId = matchingTemplate?.id || null;
    selectedTemplate = copy(config);
    for (const [value, effect] of Object.entries(state.effects)) { const option = document.createElement('option'); option.value = value; option.textContent = effect.label; $('effect').append(option); }
    buildKeyboard(); updateControls(); renderTemplates(); renderProfiles(); updateStartup(); renderSystem(state.system); connection(); await preview();
    if (state.active && !state.demo) {
      $('applied-status').textContent = '✓ Applied to keyboard';
      $('applied-status').classList.add('applied');
    } else if (state.startup.config) {
      $('applied-status').textContent = 'Saved startup design';
    }
    for (const el of document.querySelectorAll('[data-page]')) el.addEventListener('click', () => showPage(el.dataset.page));
    for (const el of document.querySelectorAll('[data-go]')) el.addEventListener('click', () => showPage(el.dataset.go));
    for (const el of document.querySelectorAll('[data-filter]')) el.addEventListener('click', () => { filter = el.dataset.filter; document.querySelectorAll('[data-filter]').forEach(b => b.classList.toggle('active', b === el)); renderTemplates(); });
    $('theme-search').addEventListener('input', e => { themeSearch = e.target.value.trim().toLocaleLowerCase(); renderTemplates(); });
    for (const el of document.querySelectorAll('[data-pattern]')) el.addEventListener('click', () => { config.pattern = el.dataset.pattern; config.overrides = {}; changed(); });
    for (let i = 0; i < 3; i++) $(`color-${i}`).addEventListener('input', e => { config.colors[i] = e.target.value; changed(); });
    $('effect').addEventListener('change', e => { config.effect = e.target.value; painting = false; changed(); });
    $('brightness').addEventListener('input', e => { config.brightness = Number(e.target.value); changed(); });
    $('background').addEventListener('input', e => { config.background = Number(e.target.value); changed(); });
    $('speed').addEventListener('input', e => { config.speed = Number(e.target.value); changed(); });
    $('reverse-colors').addEventListener('click', () => { config.reverse = !config.reverse; changed(); });
    $('reset-design').addEventListener('click', () => { config = copy(selectedTemplate); painting = false; changed(); });
    $('paint-toggle').addEventListener('click', () => { painting = !painting; updateControls(); });
    $('clear-paint').addEventListener('click', () => { config.overrides = {}; changed(); });
    $('power-button').addEventListener('click', async () => { if (config.brightness) { previousBrightness = config.brightness; config.brightness = 0; } else { config.brightness = previousBrightness || 70; } changed(); await apply(false); });
    $('apply-once').addEventListener('click', () => apply(false));
    $('apply-remember').addEventListener('click', () => apply(true));
    $('save-profile').addEventListener('click', openSave); $('library-new').addEventListener('click', openSave);
    $('cancel-save').addEventListener('click', () => $('save-dialog').close());
    $('profile-form').addEventListener('submit', async e => {
      e.preventDefault(); const button = e.submitter; button.disabled = true;
      try { const result = await api('/api/profiles/save', {name: $('profile-name').value, config}); state.profiles = result.profiles; currentName = result.profile.name; updateControls(); renderProfiles(); $('save-dialog').close(); toast('Saved to your profile library.'); }
      catch (error) { toast(error.message, true); } finally { button.disabled = false; }
    });
    $('startup-toggle').addEventListener('change', async e => {
      const enabled = e.target.checked; setBusy(true);
      try { const result = await api('/api/remember', {config: state.startup.config || config, name: state.startup.config ? state.startup.name : currentName, enabled}); state.startup = result.startup; toast(enabled ? 'Boot restore enabled.' : 'Boot restore paused. Current lighting is unchanged.'); }
      catch (error) { toast(error.message, true); } finally { updateStartup(); setBusy(false); }
    });
    $('startup-current').addEventListener('click', async () => { await apply(true); });
    $('copy-address').addEventListener('click', async () => { try { await navigator.clipboard.writeText(location.origin); toast('Local address copied.'); } catch { toast(location.origin); } });
    $('system-refresh').addEventListener('click', refreshSystem);
    window.setInterval(refreshSystem, 5000);
  } catch (e) { $('connection-banner').classList.remove('hidden'); $('connection-banner').textContent = e.message; }
}
init();
