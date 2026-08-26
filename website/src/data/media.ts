/**
 * Every image / video slot on the site lives here.
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

export interface MediaSlot {
  kind: MediaKind;
  /** Path relative to the site root for image/video, or a video ID for youtube. */
  src: string;
  alt: string;
  poster?: string;
  caption?: string;
  /** CSS aspect-ratio for the frame, e.g. "16 / 9". */
  aspect?: string;
  placeholder?: boolean;
  /** Shot description shown on placeholders (what to record). */
  expects?: string;
}

export const media = {
  hero: {
    kind: "video",
    src: "media/placeholder-hero.svg",
    alt: "EasySlice Print demo: drawing a freehand cut, building the parts and exploding them",
    aspect: "16 / 9",
    placeholder: true,
    expects: "20–40 s screen recording: draw a Freehand cut → Build → Exploded View → Export",
  },
  stepCut: {
    kind: "image",
    src: "media/placeholder-step-1.svg",
    alt: "Viewport while drawing a cut line over the model",
    placeholder: true,
    expects: "Viewport mid-draw, the cut line overlay visible",
  },
  stepConnectors: {
    kind: "image",
    src: "media/placeholder-step-2.svg",
    alt: "Built parts in exploded view showing the pin and socket",
    placeholder: true,
    expects: "Built parts in Exploded View, pin and socket visible",
  },
  stepExport: {
    kind: "image",
    src: "media/placeholder-step-3.svg",
    alt: "Export panel with the parts written as STL files",
    placeholder: true,
    expects: "Export panel with the folder and format, exported parts in the slicer",
  },
  planeCut: {
    kind: "video",
    src: "media/placeholder-plane.svg",
    alt: "Plane cut: dragging a line across a model in Plan Mode",
    placeholder: true,
    expects: "Plan Mode: drag a Plane cut, then Edit Cut Surface and move the plane with G/R",
  },
  curveCut: {
    kind: "video",
    src: "media/placeholder-curve.svg",
    alt: "Curve cut: drawing a curved line over the model",
    placeholder: true,
    expects: "Plan Mode: draw a Curve cut across the silhouette, drag a few control points",
  },
  freehandCut: {
    kind: "video",
    src: "media/placeholder-freehand.svg",
    alt: "Freehand cut: drawing a closed loop around a neck while orbiting",
    placeholder: true,
    expects: "Plan Mode: Freehand loop around a neck/wrist, orbiting with MMB between strokes",
  },
  buildExport: {
    kind: "video",
    src: "media/placeholder-build.svg",
    alt: "Build, Back to Plan, Approve and Export",
    placeholder: true,
    expects: "Build → parts appear → Back to Plan → tweak → Approve → Export STL",
  },
  quickCut: {
    kind: "video",
    src: "media/placeholder-quick.svg",
    alt: "Quick Cut: one plane cut with automatic connector, no history",
    placeholder: true,
    expects: "Quick Cut mode: one drag, parts and connector appear immediately",
  },
  connectors: {
    kind: "image",
    src: "media/placeholder-connectors.svg",
    alt: "Connector shapes: cylinder, tapered, hexagon, box and a custom mesh",
    placeholder: true,
    expects: "Close-up of the five connector shapes side by side, pins and sockets",
  },
} satisfies Record<string, MediaSlot>;
