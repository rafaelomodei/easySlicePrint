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
| `src/i18n/en.ts` | **all English copy** — the reference dictionary |
| `src/i18n/pt.ts`, `src/i18n/es.ts` | the Portuguese and Spanish translations, typed against `en.ts` |
| `src/i18n/index.ts` | language list, URL helpers, `{placeholder}` substitution |
| `src/data/media.ts` | every image / video slot on the page (the `alt` text lives in the dictionaries) |
| `src/pages/[...lang].astro` | the landing page, rendered once per language |
| `src/components/Media.astro` | renders a slot: image, self-hosted video, YouTube embed or placeholder |
| `public/media/` | placeholder illustrations now; real screenshots and clips later |

## Languages

The site ships in English, Portuguese and Spanish:

| URL | Language |
|---|---|
| `/` | English (default, no prefix) |
| `/pt/` | Português (pt-BR) |
| `/es/` | Español |

**Automatic switching.** The English page carries a tiny inline script (`src/layouts/Base.astro`)
that runs before the page paints:

1. If the visitor already picked a language from the header, it goes to that one — a manual choice
   always wins.
2. Otherwise it walks `navigator.languages` and redirects to the first supported match, so a
   browser set to `pt-BR` lands on `/pt/`.
3. Anything else stays on English.

The picker in the header is made of plain links, so the site still works with JavaScript disabled;
the script only stores the choice in `localStorage` under `esp-lang`. Every page emits
`hreflang` alternates and `x-default`, so search engines index the three versions correctly.

**Changing copy.** Edit `src/i18n/en.ts` first, then mirror the change in `pt.ts` and `es.ts` — both
are typed as `Dict` (the shape of `en.ts`), so a missing or renamed key fails the build. Notes:

* `{name}`, `{version}`, `{blenderMin}`, `{blenderMax}`, `{license}`, `{author}` and `{year}` are
  substituted from `src/data/site.ts` anywhere in a dictionary.
* Inline HTML (`<strong>`, `<em>`, `<code>`, `<kbd>`) is allowed and rendered as-is.
* Blender / add-on UI labels (Plan Mode, Build, Back to Plan, Check Mesh, …) stay in English in
  every language — that is what the user sees on screen.

**Adding a fourth language:** create `src/i18n/<code>.ts` from `en.ts`, register it in the
`dictionaries`, `languages` and `htmlLang` maps in `src/i18n/index.ts`, and that is it — the route,
the picker, the `hreflang` tags and the auto-detection pick it up.

## Replacing the placeholder media

Every slot in `src/data/media.ts` is currently `placeholder: true` and shows an illustration plus a
short description of what to record — `media.<slot>.expects` in the dictionaries, the same shot list
as `docs/media/README.md`. To publish the real material:

1. Drop the file in `public/media/` (keep clips short and small — they ship with the site) **or**
   upload it to YouTube.
2. Edit the slot:
   ```ts
   hero: { kind: "video", src: "media/demo.mp4", poster: "media/demo-poster.jpg" },
   // or
   hero: { kind: "youtube", src: "VIDEO_ID" },
   // or
   stepCut: { kind: "image", src: "media/step-1-cut.png" },
   ```
3. Remove the `placeholder` flag. The `alt` text is translated copy and lives under `media.*` in
   `src/i18n/{en,pt,es}.ts` — update it there if the new footage shows something different; the
   `expects` hint is only rendered while the slot is a placeholder, so it can stay.

## Deploying

* The workflow builds with `BASE_PATH=/easySlicePrint` and `SITE_URL=https://rafaelomodei.github.io`.
* In the repository settings, **Pages → Source** must be set to **GitHub Actions** once.
* For a custom domain later: add a `CNAME` file in `public/`, and set `SITE_URL` / `BASE_PATH=/`
  in the workflow's build step.

## Still to do before launch

- [ ] Real demo video and screenshots (see `docs/media/README.md`)
- [ ] `public/og.png` (1200×630) for link previews — the layout already emits the meta tags, add
      `<meta property="og:image">` in `src/layouts/Base.astro` when the file exists
