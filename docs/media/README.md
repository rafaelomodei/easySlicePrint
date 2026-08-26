# Media assets for the README

The README references these files (currently commented out — uncomment the
`TODO(media)` blocks in `README.md` and `README.pt-BR.md` once the files exist).

| File | What to capture | Notes |
|---|---|---|
| `demo.gif` | 10–20 s loop: draw a Freehand cut → Build → Exploded View → Export | The hero shot. Keep it under ~5 MB so GitHub renders it inline; 720 px wide, 12–15 fps |
| `step-1-cut.png` | The viewport mid-draw, cut line/loop overlay visible | Same model and camera angle in all three shots |
| `step-2-connectors.png` | Built parts in exploded view, pin and socket visible | |
| `step-3-export.png` | The Export panel / the exported parts laid out | |

Tips:

* Use a recognisable model (a bust or a figurine reads better than a cube) and a
  millimetre scene, so the panel values look realistic.
* Hide the N-panel clutter: only the **EasySlice** tab open.
* Record with Blender's own screencast or any GIF recorder; crop to the viewport
  plus the EasySlice panel.
* Keep the total of this folder small — these files ship in the git history, not
  in the extension zip (`scripts/build.sh` only packs `easy_slice_print/`).
