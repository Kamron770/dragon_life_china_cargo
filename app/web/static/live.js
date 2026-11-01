/* Live panel: checks the server every few seconds and refreshes the page content by itself.
 *
 * - Parts of the page marked with data-live="..." (cargo list, counters, clients) are
 *   re-fetched and swapped in place; filters, search and scroll stay as they are.
 * - New cargo: short sound, a pop-up, "(N)" in the browser tab and, if allowed,
 *   a desktop notification.
 */
(function () {
  const T = window.LIVE_TEXT || {};
  const INTERVAL = 10000;
  const $ = id => document.getElementById(id);
  const baseTitle = document.title;

  let base = null;       // last server state we have shown
  let unseen = 0;        // new cargo since the page was opened
  let pending = false;   // a refresh waits until the user finishes editing
  let audio = null;

  // ---- sound (browsers allow it only after the user has clicked once) ----
  function unlockAudio() {
    if (audio) return;
    try { audio = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {}
  }
  document.addEventListener('pointerdown', unlockAudio, { once: true });
  document.addEventListener('keydown', unlockAudio, { once: true });

  function beep() {
    if (!audio) return;
    try {
      [0, 0.18].forEach((delay, i) => {
        const o = audio.createOscillator(), g = audio.createGain();
        o.frequency.value = i ? 1046 : 784;
        g.gain.setValueAtTime(0.0001, audio.currentTime + delay);
        g.gain.exponentialRampToValueAtTime(0.25, audio.currentTime + delay + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + delay + 0.16);
        o.connect(g).connect(audio.destination);
        o.start(audio.currentTime + delay);
        o.stop(audio.currentTime + delay + 0.17);
      });
    } catch (e) {}
  }

  // ---- desktop notifications ----
  const btn = $('notifyBtn');
  if (btn && 'Notification' in window && Notification.permission === 'default') {
    btn.hidden = false;
    btn.addEventListener('click', async () => {
      unlockAudio();
      try { await Notification.requestPermission(); } catch (e) {}
      btn.hidden = true;
    });
  }
  function desktopNotify(text) {
    if (!('Notification' in window) || Notification.permission !== 'granted' || !document.hidden) return;
    try {
      const n = new Notification(T.notify_title || 'Dragon Life Cargo', { body: text, icon: '/static/favicon.png', tag: 'dl-new-cargo' });
      n.onclick = () => { window.focus(); location.href = '/'; };
    } catch (e) {}
  }

  // ---- pop-up and tab title ----
  function showNew(n) {
    unseen += n;
    const text = (T.new_cargo || 'New: {n}').replace('{n}', unseen);
    $('liveToastText').textContent = text;
    $('liveToast').hidden = false;
    document.title = `(${unseen}) ${baseTitle}`;
    beep();
    desktopNotify(text);
  }
  function clearNew() {
    unseen = 0;
    $('liveToast').hidden = true;
    document.title = baseTitle;
  }
  $('liveToastClose').addEventListener('click', clearNew);

  // ---- swap live parts of the page ----
  function userIsEditing() {
    const a = document.activeElement;
    return a && a.closest && a.closest('[data-live]') && /^(INPUT|SELECT|TEXTAREA)$/.test(a.tagName);
  }

  async function refreshParts(newSinceId) {
    const parts = document.querySelectorAll('[data-live]');
    if (!parts.length) return;
    if (userIsEditing()) { pending = true; return; }
    pending = false;
    let html;
    try {
      const r = await fetch(location.href, { headers: { 'X-Live': '1' }, cache: 'no-store', credentials: 'same-origin' });
      if (!r.ok || r.redirected) return;
      html = await r.text();
    } catch (e) { return; }
    if (userIsEditing()) { pending = true; return; }
    const doc = new DOMParser().parseFromString(html, 'text/html');
    parts.forEach(el => {
      const fresh = doc.querySelector(`[data-live="${el.dataset.live}"]`);
      if (fresh) el.replaceWith(document.adoptNode(fresh));
    });
    // highlight rows that just appeared
    document.querySelectorAll('[data-live] tr[data-id]').forEach(tr => {
      if (Number(tr.dataset.id) > newSinceId) tr.classList.add('row-new');
    });
  }

  // ---- polling ----
  async function poll() {
    if (document.hidden && base) return;  // the tab is in the background: check when it comes back
    let state;
    try {
      const r = await fetch('/api/updates' + (base ? `?since_id=${base.last_id}` : ''), { cache: 'no-store', credentials: 'same-origin' });
      if (r.status === 401) { clearInterval(timer); return; }
      if (!r.ok) return;
      state = await r.json();
    } catch (e) { return; }  // offline / server waking up — try again next time

    if (!base) { base = state; return; }
    const changed = state.total !== base.total || state.changed !== base.changed ||
                    state.last_id !== base.last_id || state.last_client !== base.last_client;
    if (state.new_count > 0) showNew(state.new_count);
    if (changed || pending) await refreshParts(base.last_id);
    base = state;
  }

  let timer = setInterval(poll, INTERVAL);
  poll();
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    poll();
    if (location.pathname === '/' && unseen) setTimeout(clearNew, 4000);  // operator is looking at the list
  });
  // finished editing a field inside the list → apply the refresh that was waiting
  document.addEventListener('focusout', () => { if (pending) setTimeout(() => refreshParts(base ? base.last_id : 0), 300); });
})();
