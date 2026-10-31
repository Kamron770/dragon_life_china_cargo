/* Phone camera barcode scanner for the "Skanerlash" page.
 *
 * Reads the camera at full resolution (small-screen previews are too coarse for long
 * parcel barcodes). Uses the phone's built-in BarcodeDetector when it exists (Android
 * Chrome), otherwise the bundled ZXing decoder (iPhone, others).
 *
 * Expects on the page: #camStart #camStop #camTorch #camMsg #camBox #camVideo #camHint,
 * and window.SCAN_TEXT with the error messages.
 */
(function () {
  const T = window.SCAN_TEXT || {};
  const $ = id => document.getElementById(id);
  const FORMATS_NATIVE = ['code_128', 'code_39', 'code_93', 'ean_13', 'ean_8', 'upc_a', 'upc_e', 'itf', 'codabar', 'qr_code'];

  let stream = null, timer = null, busy = false, done = false;
  let detector = null, zxReader = null, torchOn = false;
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d', { willReadFrequently: true });

  function showError(text) { const m = $('camMsg'); m.textContent = text; m.hidden = false; }
  function ui(running) {
    $('camStart').hidden = running;
    $('camStop').hidden = !running;
    $('camBox').hidden = !running;
    $('camHint').hidden = !running;
    if (!running) $('camTorch').hidden = true;
  }

  async function makeNativeDetector() {
    if (!('BarcodeDetector' in window)) return null;
    try {
      const supported = await BarcodeDetector.getSupportedFormats();
      const formats = FORMATS_NATIVE.filter(f => supported.includes(f));
      return formats.includes('code_128') ? new BarcodeDetector({ formats }) : null;
    } catch (e) { return null; }
  }

  function makeZxing() {
    if (typeof ZXing === 'undefined') return null;
    const F = ZXing.BarcodeFormat;
    const hints = new Map();
    hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [F.CODE_128, F.CODE_39, F.CODE_93, F.EAN_13, F.EAN_8,
      F.UPC_A, F.UPC_E, F.ITF, F.CODABAR, F.QR_CODE]);
    hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
    const reader = new ZXing.MultiFormatReader();
    reader.setHints(hints);
    return reader;
  }

  // Middle band of the frame at native resolution: where the on-screen guide box is.
  function grabBand(video) {
    const vw = video.videoWidth, vh = video.videoHeight;
    if (!vw || !vh) return false;
    const w = Math.round(vw * 0.94), h = Math.round(vh * 0.5);
    canvas.width = w; canvas.height = h;
    ctx.drawImage(video, (vw - w) / 2, (vh - h) / 2, w, h, 0, 0, w, h);
    return true;
  }

  async function decodeOnce(video) {
    if (detector) {
      const codes = await detector.detect(video);
      if (codes.length) return codes[0].rawValue;
    }
    if (zxReader && grabBand(video)) {
      try {
        const source = new ZXing.HTMLCanvasElementLuminanceSource(canvas);
        const result = zxReader.decode(new ZXing.BinaryBitmap(new ZXing.HybridBinarizer(source)));
        return result.getText();
      } catch (e) { /* nothing in this frame */ }
    }
    return null;
  }

  // The parcel just handled is often still in front of the camera when it reopens:
  // ignore that same code for a few seconds so it is not processed twice.
  const REPEAT_MS = 8000;
  function isRecentRepeat(code) {
    try {
      const last = JSON.parse(sessionStorage.getItem('dl_last') || 'null');
      return last && last.code === code && Date.now() - last.at < REPEAT_MS;
    } catch (e) { return false; }
  }
  function remember(code) {
    try { sessionStorage.setItem('dl_last', JSON.stringify({ code, at: Date.now() })); } catch (e) {}
  }

  async function tick() {
    if (busy || done || !stream) return;
    busy = true;
    try {
      const raw = await decodeOnce($('camVideo'));
      const text = raw && raw.trim();
      if (text && !isRecentRepeat(text)) {
        remember(text);
        done = true;
        if (navigator.vibrate) navigator.vibrate(120);
        stop();
        location.href = '/scan?code=' + encodeURIComponent(text);
      }
    } catch (e) { /* keep scanning */ }
    busy = false;
  }

  function stop() {
    clearInterval(timer); timer = null;
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = null;
    const v = $('camVideo'); v.srcObject = null;
    ui(false);
  }

  async function start() {
    $('camMsg').hidden = true;
    if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return showError(T.https);
    }
    detector = await makeNativeDetector();
    zxReader = makeZxing();
    if (!detector && !zxReader) return showError(T.lib);

    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
    } catch (err) {
      stream = null;
      const name = (err && err.name) || String(err);
      if (/NotAllowed|Permission|Security/i.test(name)) showError(T.denied);
      else if (/NotFound|Overconstrained|NotReadable|Abort/i.test(name)) showError(T.nocam);
      else showError(T.other + ' ' + name);
      return;
    }

    const video = $('camVideo');
    video.setAttribute('playsinline', ''); // iPhone: play inside the page, not fullscreen
    video.muted = true;
    video.srcObject = stream;
    ui(true);
    try { await video.play(); } catch (e) {}

    const track = stream.getVideoTracks()[0];
    try { await track.applyConstraints({ advanced: [{ focusMode: 'continuous' }] }); } catch (e) {}
    try {
      const caps = track.getCapabilities ? track.getCapabilities() : {};
      $('camTorch').hidden = !caps.torch;
    } catch (e) {}

    done = false;
    timer = setInterval(tick, 150);
  }

  async function toggleTorch() {
    if (!stream) return;
    torchOn = !torchOn;
    try { await stream.getVideoTracks()[0].applyConstraints({ advanced: [{ torch: torchOn }] }); } catch (e) {}
  }

  $('camStart').addEventListener('click', () => {
    try { sessionStorage.setItem('dl_cam', '1'); } catch (e) {}
    start();
  });
  $('camStop').addEventListener('click', () => {
    try { sessionStorage.removeItem('dl_cam'); } catch (e) {}
    stop();
  });
  $('camTorch').addEventListener('click', toggleTorch);
  window.addEventListener('pagehide', stop);

  // Back on an empty scan page after a camera scan → reopen the camera for the next parcel
  try {
    if (window.SCAN_AUTOSTART && sessionStorage.getItem('dl_cam') === '1') start();
  } catch (e) {}
})();
