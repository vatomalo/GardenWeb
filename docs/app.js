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

try {
  const storefront = new URL(config.storefrontUrl);
  if (storefront.protocol !== 'https:' || storefront.username || storefront.password) {
    throw new Error('Use an HTTPS storefront URL.');
  }
  if (frame.src !== storefront.href) frame.src = storefront.href;
  direct.href = storefront.href;
} catch {
  // Keep the verified source-site address when configuration is invalid.
}

const orderShell = document.querySelector('#order-shell');
const orderViewControl = document.querySelector('#order-view-control');
const orderHint = document.querySelector('#order-hint');

orderViewControl.addEventListener('click', () => {
  const loginMode = orderShell.classList.toggle('is-login-mode');
  orderViewControl.setAttribute('aria-pressed', String(loginMode));
  orderViewControl.textContent = loginMode ? 'Vis hele menyen' : 'Logg inn / velg takeaway';
  orderHint.textContent = loginMode
    ? 'Logg inn, velg takeaway eller fullfør bestillingen her. Gå tilbake til hele menyen når du er klar.'
    : 'Hele menyen er tilgjengelig nedenfor. Bruk knappen for å logge inn eller velge takeaway.';
  // Never scroll or reload the cross-origin iframe automatically.
});
