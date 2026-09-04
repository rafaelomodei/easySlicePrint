// The manifest is imported as text at build time so the version shown on the
// site (and the download URL) never drifts from what is actually released.
import manifest from "../../../easy_slice_print/blender_manifest.toml?raw";

/**
 * Single source of truth for names, links and the current version.
 *
 * Everything that is *copy* (tagline, description, labels) lives in
 * `src/i18n/{en,pt,es}.ts` instead — see `src/i18n/index.ts`.
 */
const version = manifest.match(/^version\s*=\s*"([^"]+)"/m)?.[1] ?? "0.0.0";
const blenderMin = manifest.match(/^blender_version_min\s*=\s*"([^"]+)"/m)?.[1] ?? "4.2.0";

const repo = "rafaelomodei/easySlicePrint";
const repoUrl = `https://github.com/${repo}`;

export const site = {
  name: "EasySlice Print",
  author: "Rafael Omodei",
  version,
  blenderMin: blenderMin.replace(/\.0$/, ""),
  blenderMax: "5.2",
  license: "GPL-3.0-or-later",
  repo,
  repoUrl,
  links: {
    releases: `${repoUrl}/releases`,
    // Listing on the Blender Extensions platform. While it is under review the public
    // page (/add-ons/easy-slice-print/) 404s, so point at the queue entry until then.
    blenderExtension: "https://extensions.blender.org/approval-queue/easy-slice-print/",
    latestRelease: `${repoUrl}/releases/latest`,
    downloadZip: `${repoUrl}/releases/download/v${version}/easy_slice_print-${version}.zip`,
    issues: `${repoUrl}/issues`,
    newIssue: `${repoUrl}/issues/new/choose`,
    discussions: `${repoUrl}/discussions`,
    changelog: `${repoUrl}/blob/main/CHANGELOG.md`,
    architecture: `${repoUrl}/blob/main/docs/ARCHITECTURE.md`,
    features: `${repoUrl}/blob/main/docs/FEATURES.md`,
    contributing: `${repoUrl}/blob/main/CONTRIBUTING.md`,
    license: `${repoUrl}/blob/main/LICENSE`,
    readme: `${repoUrl}/blob/main/README.md`,
    readmePtBr: `${repoUrl}/blob/main/README.pt-BR.md`,
    security: `${repoUrl}/blob/main/SECURITY.md`,
  },
} as const;
