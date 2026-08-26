// The manifest is imported as text at build time so the version shown on the
// site (and the download URL) never drifts from what is actually released.
import manifest from "../../../easy_slice_print/blender_manifest.toml?raw";

/** Single source of truth for names, links and the current version. */
const version = manifest.match(/^version\s*=\s*"([^"]+)"/m)?.[1] ?? "0.0.0";
const blenderMin = manifest.match(/^blender_version_min\s*=\s*"([^"]+)"/m)?.[1] ?? "4.2.0";

const repo = "rafaelomodei/easySlicePrint";
const repoUrl = `https://github.com/${repo}`;

export const site = {
  name: "EasySlice Print",
  tagline: "Cut. Connect. Print.",
  description:
    "Non-destructive model splitting and custom connectors for 3D printing — a free, open-source Blender add-on.",
  author: "Rafael Omodei",
  version,
  blenderMin: blenderMin.replace(/\.0$/, ""),
  blenderMax: "5.2",
  license: "GPL-3.0-or-later",
  repo,
  repoUrl,
  links: {
    releases: `${repoUrl}/releases`,
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
    readmePtBr: `${repoUrl}/blob/main/README.pt-BR.md`,
    security: `${repoUrl}/blob/main/SECURITY.md`,
  },
} as const;

export const nav = [
  { href: "#workflow", label: "Workflow" },
  { href: "#plan-mode", label: "Plan Mode" },
  { href: "#connectors", label: "Connectors" },
  { href: "#features", label: "Features" },
  { href: "#install", label: "Install" },
  { href: "#faq", label: "FAQ" },
] as const;
