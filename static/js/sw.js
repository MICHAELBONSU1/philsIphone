// Phil's iPhone - Background Service Worker
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// This presence helps mobile browsers (especially Chrome/Android) 
// prioritize the site's background Socket.IO connection.