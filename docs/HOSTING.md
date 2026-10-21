# Hosted server

Cloudflare Tunnel connects to Nginx on `127.0.0.1:9900`. Nginx serves the Bun
output in `.local/website/dist` directly. Only `/api/` is proxied to the Python
game/application backend on `127.0.0.1:9901`. HTML, images, fonts, videos, Ruffle,
and downloadable clients are static files; serving them does not require Python.

The generated `resources/config.json` includes the server-mode 3D override.
The launcher diagnostics path `/__mock_trace` returns 204 directly from Nginx.
Accounts, administration, contributions, activity events, and live gameplay
continue to require the backend APIs. A static host without an API proxy can
display pages, but cannot provide those interactive features.

## Build and publish

```sh
bun run build:website
bun run check:site
```

The build atomically replaces `.local/website/dist`. Nginx immediately serves
the new files; no Python restart or Nginx reload is needed for content updates.
Source HTML/CSS/JavaScript and legal Markdown remain unchanged. Generated output
is ignored by Git. Use `--output /path/to/public` for a different destination and
update Nginx's `root` to match. The frontend compiler runs in Bun and uses FFmpeg
and `avifenc` to generate cached responsive images. Other media exporters use
the Python/FFmpeg/FFDec pipeline documented in [Website](WEBSITE.md).

The configuration is `ops/nginx/boufbowl.conf`, installed at
`/etc/nginx/sites-available/boufbowl` and linked from `sites-enabled`.
It contains the current server's absolute public-folder path; adapt it when
deploying elsewhere. Nginx needs read/traverse permission on the public directory
and its ancestors. On this instance its user has only a traversal ACL on the
otherwise private home directory:

```sh
sudo setfacl -m u:www-data:x /home/ubuntu
sudo install -m 0644 ops/nginx/boufbowl.conf /etc/nginx/sites-available/boufbowl
sudo nginx -t
sudo systemctl reload nginx
```

## Caching and compression

HTML and JSON revalidate on each visit. Bun generates script filenames containing
their content hash; these receive a one-year immutable cache lifetime. Media URLs
receive a revision derived from their contents and a 30-day cache lifetime.
Download package URLs revalidate because their filenames stay stable. Missing
files do not receive these long-lived cache headers.

Brotli and gzip compress public text/WebAssembly responses. Install the Ubuntu
packages `libnginx-mod-http-brotli-filter` and `libnginx-mod-http-brotli-static`
before loading this configuration. API buffering and compression are disabled
for long polling/uploads. The 24 MB proxy upload ceiling accommodates the
application's 20 MB upload limit; Python still enforces authorization and limits.

Static requests are logged by Nginx, rather than observed by Python's asset
counter. Browser-reported section, character, and download activity still use
`/api/site-events`. No Nginx proxy cache is enabled.

## Operations

```sh
systemctl --user status boufbowl-server.service boufbowl-healthcheck.timer
journalctl --user -u boufbowl-server.service -f
curl -I http://127.0.0.1:9900/                 # Static HTML from Nginx
curl -fsS http://127.0.0.1:9900/api/health     # API through Nginx
curl -fsS http://127.0.0.1:9901/api/health     # Python directly
```

The backend starts at boot, restarts after crashes, and has a health timer on
port 9901. Nginx also starts at boot. Nginx is shared with PRMX, so validate its
complete configuration before reloading. Logs are
`/var/log/nginx/boufbowl-access.log` and `/var/log/nginx/boufbowl-error.log`.
