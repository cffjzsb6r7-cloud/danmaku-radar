/*
 * API endpoint selected at runtime:
 * - GitHub Pages keeps using the public API service.
 * - A custom domain served by FastAPI automatically uses same-origin API calls.
 * Override this file for another host without editing app.js.
 */
(function () {
  if (window.DANMAKU_API) return;
  var host = window.location.hostname;
  window.DANMAKU_API = host.endsWith('github.io')
    ? 'https://danmaku-radar-api.onrender.com'
    : window.location.origin;
})();
