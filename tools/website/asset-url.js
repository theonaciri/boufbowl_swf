// Bun supplies a revision derived from the media files at build time.
export function assetUrl(path) {
  if (!path || typeof __SITE_ASSET_VERSION__ === "undefined") return path;
  const [pathname, query = ""] = path.split("?", 2);
  const params = new URLSearchParams(query);
  params.set("v", __SITE_ASSET_VERSION__);
  return `${pathname}?${params}`;
}
