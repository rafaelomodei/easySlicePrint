# EasySlice Print — website

Public landing page for the add-on, built with [Astro](https://astro.build) and published to
GitHub Pages by `.github/workflows/pages.yml` on every push to `main` that touches `website/`.

```bash
cd website
npm install
npm run dev       # http://localhost:4321/easySlicePrint/
npm run build     # static output in website/dist/
npm run preview
```

## Where things are

| Path | What |
|---|---|
| `src/data/site.ts` | name, links, download URL. The **version** is read from `easy_slice_print/blender_manifest.toml` at build time |
| `src/data/media.ts` | every image / video slot on the page |
| `src/pages/index.astro` | the landing page (copy lives here) |
| `src/components/Media.astro` | renders a slot: image, self-hosted video, YouTube embed or placeholder |
| `public/media/` | placeholder illustrations now; real screenshots and clips later |

## Replacing the placeholder media

Every slot in `src/data/media.ts` is currently `placeholder: true` and shows an illustration plus a
short description of what to record (the same shot list as `docs/media/README.md`). To publish the
real material:

1. Drop the file in `public/media/` (keep clips short and small — they ship with the site) **or**
   upload it to YouTube.
2. Edit the slot:
   ```ts
   hero: { kind: "video", src: "media/demo.mp4", poster: "media/demo-poster.jpg", alt: "..." },
   // or
   hero: { kind: "youtube", src: "VIDEO_ID", alt: "..." },
   // or
   stepCut: { kind: "image", src: "media/step-1-cut.png", alt: "..." },
   ```
3. Remove `placeholder` and `expects`.

## Deploying

* The workflow builds with `BASE_PATH=/easySlicePrint` and `SITE_URL=https://rafaelomodei.github.io`.
* In the repository settings, **Pages → Source** must be set to **GitHub Actions** once.
* For a custom domain later: add a `CNAME` file in `public/`, and set `SITE_URL` / `BASE_PATH=/`
  in the workflow's build step.

## Still to do before launch

- [ ] Real demo video and screenshots (see `docs/media/README.md`)
- [ ] `public/og.png` (1200×630) for link previews — the layout already emits the meta tags, add
      `<meta property="og:image">` in `src/layouts/Base.astro` when the file exists
