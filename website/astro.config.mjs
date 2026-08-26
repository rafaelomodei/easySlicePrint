// @ts-check
import { defineConfig } from "astro/config";

// GitHub Pages serves a project site under https://<user>.github.io/<repo>/.
// Override both values with env vars when the site moves to a custom domain
// (SITE_URL=https://example.com BASE_PATH=/ npm run build).
const site = process.env.SITE_URL ?? "https://rafaelomodei.github.io";
const base = process.env.BASE_PATH ?? "/easySlicePrint";

export default defineConfig({
  site,
  base,
  trailingSlash: "ignore",
  compressHTML: false, // keeps the whitespace between inline text and <strong>/<code>
  output: "static",
  build: { format: "directory" },
  vite: {
    // src/data/site.ts imports ../easy_slice_print/blender_manifest.toml
    server: { fs: { allow: [".."] } },
  },
});
