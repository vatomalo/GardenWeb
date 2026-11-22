'use strict';
const config = window.GARDEN_WEORDER;
const video = document.querySelector('#opening');
const filmControl = document.querySelector('#film-control');
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

function updateFilmControl() {
  filmControl.textContent = video.paused ? 'Spill åpningsfilmen' : 'Sett filmen på pause';
}
async function playFilm() {
  try { await video.play(); } catch { updateFilmControl(); }
}
if (video && filmControl) {
  filmControl.hidden = false;
  video.addEventListener('play', updateFilmControl);
  video.addEventListener('pause', updateFilmControl);
  filmControl.addEventListener('click', () => video.paused ? playFilm() : video.pause());
  reducedMotion.addEventListener('change', e => { if (e.matches) video.pause(); });
  if (!reducedMotion.matches) playFilm();
  updateFilmControl();
}

const frame = document.querySelector('#weorder');
const direct = document.querySelector('#order-direct');
const orderShell = document.querySelector('#order-shell');
const orderViewControl = document.querySelector('#order-view-control');
const orderHint = document.querySelector('#order-hint');
const takeawayHint = orderHint.textContent;
const sound = document.querySelector('#sound-control');
const audio = new Audio('assets/order-chime.wav');
const completed = new Set();
let soundEnabled = false;
let storefrontOrigin = null;

try {
  const storefront = new URL(config.storefrontUrl);
  if (storefront.protocol !== 'https:' || storefront.username || storefront.password) {
    throw new Error('Use an HTTPS storefront URL.');
  }
  if (frame.src !== storefront.href) frame.src = storefront.href;
  direct.href = storefront.href;
  storefrontOrigin = storefront.origin;
} catch {
  // Keep the verified source-site address when configuration is invalid.
}

function setFullMenu(showFullMenu) {
  orderShell.classList.toggle('is-full-menu', showFullMenu);
  orderViewControl.textContent = showFullMenu ? 'Tilbake til bestilling' : 'Vis hele menyen';
  orderHint.textContent = showFullMenu ? 'Gå tilbake til bestilling for å bruke kassen.' : takeawayHint;
}

orderViewControl.hidden = false;
orderViewControl.addEventListener('click', () => {
  setFullMenu(!orderShell.classList.contains('is-full-menu'));
  orderShell.scrollIntoView({
    block: 'start',
    behavior: reducedMotion.matches ? 'instant' : 'smooth'
  });
});
document.querySelectorAll('a[href="#bestill"]').forEach(link => {
  link.addEventListener('click', () => setFullMenu(false));
});

function playChime() {
  audio.currentTime = 0;
  audio.play().catch(() => {});
}
sound.hidden = false;
sound.addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  sound.setAttribute('aria-pressed', String(soundEnabled));
  sound.textContent = soundEnabled ? 'Lyd på' : 'Lyd av';
  if (soundEnabled) playChime();
});
window.addEventListener('message', event => {
  const type = config?.completionType;
  const payload = event.data;
  if (!type || storefrontOrigin !== event.origin || event.source !== frame.contentWindow ||
      !payload || typeof payload !== 'object' || payload.type !== type ||
      typeof payload.orderId !== 'string' || !payload.orderId.trim() ||
      payload.orderId.length > 128 || completed.has(payload.orderId)) return;
  completed.add(payload.orderId);
  if (soundEnabled) playChime();
});
