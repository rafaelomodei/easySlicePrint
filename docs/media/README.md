# Media assets for the README and the website

Raw screen captures are **not** committed: they stay in `media/` at the repo root, which
is gitignored. Only the compressed files below — small enough to ship in the git history
and on the site — go in.

## Recorded

| File | Shows | Where it is used |
|---|---|---|
| `docs/media/curve-cut.gif` | Quick Cut with the Curve tool on a carousel horse's tail, at 2.5× speed | README hero, both languages |
| `website/public/media/curve-cut.mp4` | the same take, full length and full quality | site `hero` and `curveCut` slots |
| `website/public/media/curve-cut-poster.jpg` | the frame at 0:48, with the tail already detached | poster for the video above |

## Still to record

| File | What to capture | Notes |
|---|---|---|
| `demo.gif` | 10–20 s loop: draw a Freehand cut → Build → Exploded View → Export | The full flow, for the README hero and the site `hero`; keep it under ~5 MB so GitHub renders it inline |
| `step-1-cut.png` | The viewport mid-draw, cut line/loop overlay visible | Same model and camera angle in all three shots |
| `step-2-connectors.png` | Built parts in exploded view, pin and socket visible | |
| `step-3-export.png` | The Export panel / the exported parts laid out | |
| plane / freehand / build / quick / connectors clips | one short take per cut type | the remaining `placeholder: true` slots in `website/src/data/media.ts` |

Tips:

* Use a recognisable model (a bust or a figurine reads better than a cube) and a
  millimetre scene, so the panel values look realistic.
* Hide the N-panel clutter: only the **EasySlice** tab open.
* Record with Blender's own screencast or any GIF recorder; crop to the viewport
  plus the EasySlice panel.
* Keep the total of this folder small — these files ship in the git history, not
  in the extension zip (`scripts/build.sh` only packs `easy_slice_print/`).

## Turning a raw capture into the committed files

A 1280×720, 54 s capture came out of the recorder at 68 MB; these three commands turn it
into a 1.9 MB video, a 90 KB poster and a 5.2 MB GIF.

The site video — full length, `controls` in `Media.astro` let the visitor follow it. The
denoiser is there because the raw file is a GIF: its dithering is noise that H.264 would
otherwise spend bitrate on.

```sh
ffmpeg -i media/<capture> \
  -vf "fps=20,hqdn3d=2:1:3:3,scale=1280:-2:flags=lanczos" \
  -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p -movflags +faststart -an \
  website/public/media/<name>.mp4
```

The poster — pick a second that shows the *result*, not the setup:

```sh
ffmpeg -ss 48 -i website/public/media/<name>.mp4 -frames:v 1 -q:v 4 \
  website/public/media/<name>-poster.jpg
```

The README GIF — sped up and cut to 10 fps, 720 px and 64 colours to land under 5 MB.
A Blender viewport is nearly greyscale, so 64 colours costs almost nothing visually:

```sh
ffmpeg -i media/<capture> -filter_complex \
  "setpts=0.4*PTS,fps=10,scale=720:-2:flags=lanczos,split[a][b];\
[a]palettegen=max_colors=64:stats_mode=diff[p];\
[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -loop 0 docs/media/<name>.gif
```

Then wire it up: `website/src/data/media.ts` for the slot (drop its `placeholder` flag) and
`website/src/i18n/{en,pt,es}.ts` under `media.<slot>.alt` for the description. The README
blocks are marked `TODO(media)` in `README.md` and `README.pt-BR.md`.
