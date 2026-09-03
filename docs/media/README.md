# Media assets for the README and the website

Raw screen captures are **not** committed: they stay in `media/` at the repo root, which
is gitignored. Only the compressed files below — small enough to ship in the git history
and on the site — go in.

## Recorded

| File | Shows | Where it is used |
|---|---|---|
| `docs/media/demo.gif` | the whole flow on a carousel horse — plane cuts on the legs, a curve cut on the head, Build, exploded parts — at 5× speed | README cover, both languages |
| `website/public/media/demo.mp4` | the same take, full length and 1600×900 so the panel stays readable | site `hero` |
| `website/public/media/plane-cut.mp4` | a plane cut planned on a leg: cut surface, connector, Build | site `planeCut` |
| `website/public/media/curve-cut.mp4` | Quick Cut with the Curve tool on the horse's tail | site `curveCut` |
| `*-poster.jpg` | one frame of each video, picked where the *result* is on screen | poster for each video above |

## Still to record

| File | What to capture | Notes |
|---|---|---|
| `step-1-cut.png` | The viewport mid-draw, cut line/loop overlay visible | Same model and camera angle in all three shots |
| `step-2-connectors.png` | Built parts in exploded view, pin and socket visible | |
| `step-3-export.png` | The Export panel / the exported parts laid out | |
| freehand / build / quick / connectors clips | one short take each | the remaining `placeholder: true` slots in `website/src/data/media.ts` |

Tips:

* Use a recognisable model (a bust or a figurine reads better than a cube) and a
  millimetre scene, so the panel values look realistic.
* Hide the N-panel clutter: only the **EasySlice** tab open.
* Record with Blender's own screencast or any GIF recorder; crop to the viewport
  plus the EasySlice panel.
* Keep the total of this folder small — these files ship in the git history, not
  in the extension zip (`scripts/build.sh` only packs `easy_slice_print/`).

## Turning a raw capture into the committed files

Captures arrive at 60–90 MB — a 102 s 1080p60 MP4, or a 1280×720 GIF from a GIF recorder.
These commands turn one into a video of a few MB, a poster and a GIF under 5 MB.

The site video — full length, `controls` in `Media.astro` let the visitor follow it. 1600×900
is worth the extra megabyte on a screen capture: the add-on's panel is part of the demo and
goes soft at 720p. `-an` because a screen capture's audio track is usually silence.

```sh
ffmpeg -i media/<capture> \
  -vf "fps=30,scale=1600:-2:flags=lanczos" \
  -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p -movflags +faststart -an \
  website/public/media/<name>.mp4
```

From a **GIF** capture, add `hqdn3d=2:1:3:3` to that `-vf` chain and drop to `fps=20`: the
recorder's dithering is noise H.264 would otherwise spend bitrate on, and a GIF holds no more
than 20 fps anyway.

The poster — pick a second that shows the *result*, not the setup:

```sh
ffmpeg -ss 48 -i website/public/media/<name>.mp4 -frames:v 1 -q:v 4 \
  website/public/media/<name>-poster.jpg
```

The README GIF — sped up and cut to 10 fps, 720 px and 64 colours to land under 5 MB. A
Blender viewport is nearly greyscale, so 64 colours costs almost nothing visually. Pick the
speed so the result runs 10–20 s: `PTS/5` took the 102 s demo down to 20 s.

```sh
ffmpeg -i media/<capture> -filter_complex \
  "setpts=PTS/5,fps=10,scale=720:-2:flags=lanczos,split[a][b];\
[a]palettegen=max_colors=64:stats_mode=diff[p];\
[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle" \
  -loop 0 docs/media/<name>.gif
```

Then wire it up: `website/src/data/media.ts` for the slot (drop its `placeholder` flag) and
`website/src/i18n/{en,pt,es}.ts` under `media.<slot>.alt` for the description. The README
cover sits right under the alpha warning in `README.md` and `README.pt-BR.md`; what is still
missing there is marked `TODO(media)`.
