/**
 * Every image / video slot on the site lives here.
 *
 * This file holds only *what to show*; the `alt` text and the "what to record"
 * hint are translated copy and live in `src/i18n/{en,pt,es}.ts` under `media.*`
 * (merged in by `localizedMedia()` in `src/i18n/index.ts`).
 *
 * While the real recordings are not done yet, each slot points to a
 * placeholder illustration in `public/media/` and is flagged `placeholder: true`,
 * which renders a "demo coming soon" overlay. To publish the real thing:
 *
 *   - image:   set `kind: "image"` and `src` to a file in `public/media/`
 *   - video:   set `kind: "video"`, `src` to an .mp4/.webm in `public/media/`
 *              (optionally `poster`) — keep files small, they ship with the site
 *   - youtube: set `kind: "youtube"` and `src` to the video ID (e.g. "dQw4w9WgXcQ")
 *
 * and remove the `placeholder` flag. The `expects` hint is only shown while the
 * slot is a placeholder, so whoever records the footage knows what to capture.
 */
export type MediaKind = "image" | "video" | "youtube";

/** The language-independent half of a slot: what file, how to frame it. */
export interface MediaSource {
  kind: MediaKind;
  /** Path relative to the site root for image/video, or a video ID for youtube. */
  src: string;
  poster?: string;
  /** CSS aspect-ratio for the frame, e.g. "16 / 9". */
  aspect?: string;
  placeholder?: boolean;
}

/** What `Media.astro` renders: a source plus the translated strings. */
export interface MediaSlot extends MediaSource {
  alt: string;
  caption?: string;
  /** Shot description shown on placeholders (what to record). */
  expects?: string;
}

export const media = {
  hero: { kind: "video", src: "media/placeholder-hero.svg", aspect: "16 / 9", placeholder: true },
  stepCut: { kind: "image", src: "media/placeholder-step-1.svg", placeholder: true },
  stepConnectors: { kind: "image", src: "media/placeholder-step-2.svg", placeholder: true },
  stepExport: { kind: "image", src: "media/placeholder-step-3.svg", placeholder: true },
  planeCut: { kind: "video", src: "media/placeholder-plane.svg", placeholder: true },
  curveCut: { kind: "video", src: "media/placeholder-curve.svg", placeholder: true },
  freehandCut: { kind: "video", src: "media/placeholder-freehand.svg", placeholder: true },
  buildExport: { kind: "video", src: "media/placeholder-build.svg", placeholder: true },
  quickCut: { kind: "video", src: "media/placeholder-quick.svg", placeholder: true },
  connectors: { kind: "image", src: "media/placeholder-connectors.svg", placeholder: true },
} satisfies Record<string, MediaSource>;
