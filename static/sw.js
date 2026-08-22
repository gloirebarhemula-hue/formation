self.addEventListener("install", (e) => {
  self.skipWaiting();
});
self.addEventListener("fech", (e) => {
  e.respondWith(fetch(e.request));
});
