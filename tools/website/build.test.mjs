import { test, expect } from "bun:test";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { buildSite } from "./build.mjs";

test("site origin is checked before building and rejects unsafe URLs", async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), "boufbowl-site-config-"));
  try {
    await mkdir(path.join(root, "resources"));
    for (const site_url of ["invalid", "http://example.com", "https://user@example.com", "https://example.com/path", "https://example.com/?q=1", "https://example.com/#part"]) {
      await writeFile(path.join(root, "resources/site.json"), JSON.stringify({ site_url }));
      await expect(buildSite({ root })).rejects.toThrow("site_url must be an HTTPS origin");
    }
    await writeFile(path.join(root, "resources/site.json"), JSON.stringify({ site_url: "https://example.com" }));
    // A valid origin reaches the next required input.
    await expect(buildSite({ root })).rejects.toThrow("release.json");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
