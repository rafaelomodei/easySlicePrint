/**
 * English copy — the reference dictionary.
 *
 * `pt.ts` and `es.ts` are typed as `Dict`, so a missing or renamed key is a
 * build error (`npm run check`). Rules for translators:
 *
 *   - Keep the inline HTML (`<strong>`, `<em>`, `<code>`, `<kbd>`) intact.
 *   - Keep the placeholders `{name}`, `{version}`, `{blenderMin}`,
 *     `{blenderMax}`, `{license}`, `{author}`, `{year}` — they are filled in
 *     from `src/data/site.ts` at build time.
 *   - Keep add-on / Blender UI labels in English (Plan Mode, Quick Cut, Build,
 *     Back to Plan, Approve, Check Mesh, Exploded View, Ready, Keep Original,
 *     Skip Failed Cuts, Edit Cut Surface, ESP_Backup, ...): that is what the
 *     user actually sees on screen.
 */

const en = {
  meta: {
    tagline: "Cut. Connect. Print.",
    description:
      "Non-destructive model splitting and custom connectors for 3D printing — a free, open-source Blender add-on.",
  },

  language: {
    label: "Language",
    names: { en: "English", pt: "Português", es: "Español" },
  },

  nav: {
    workflow: "Workflow",
    planMode: "Plan Mode",
    connectors: "Connectors",
    features: "Features",
    install: "Install",
    faq: "FAQ",
  },

  header: {
    home: "{name} home",
    sections: "Sections",
    download: "Download",
  },

  hero: {
    pillFree: "Free &amp; open source",
    pillBlender: "Blender {blenderMin} – {blenderMax}",
    pillPlatforms: "Windows · macOS · Linux",
    titleLead: "Cut. Connect.",
    titleAccent: "Print.",
    lead: "Split any model into printable parts with plane, curve or freehand cuts, add pin-and-socket connectors that actually fit, and export one file per part — without ever touching the original mesh.",
    download: "Download v{version}",
    free: "· free",
    github: "View on GitHub",
    fine: "{license} · Blender add-on · Exports STL / OBJ / FBX in millimetres",
  },

  status: {
    pill: "Alpha",
    note:
      "<strong>Alpha software.</strong> {name} is still under active development: expect bugs and rough edges. A cut can fail or come out wrong on some meshes, and a plan saved with one version may not rebuild the same way in the next. Keep a backup of your <code>.blend</code>, check every part before you print it, and report anything that goes wrong on GitHub.",
  },

  workflow: {
    eyebrow: "Workflow",
    title: "Three steps from a model to printable parts",
    intro:
      "The whole tool lives in one sidebar tab. Draw where the cut should go, let the add-on place the connectors, export.",
    steps: {
      cut: {
        title: "Draw the cut",
        body: "Drag a line for a flat cut, sketch a curve, or draw a loop around a neck or wrist directly on the surface. Cuts follow the view, so what you draw is what you get.",
      },
      connectors: {
        title: "Generate connectors",
        body: "A pin on one side, a matching socket on the other. Pick the shape and size, set the clearance for your printer, swap sides or move the connector by hand.",
      },
      export: {
        title: "Export printable parts",
        body: "One click writes one STL, OBJ or FBX per part into a folder, already in millimetres. Check the fit in Exploded View before you print.",
      },
    },
  },

  planMode: {
    eyebrow: "Plan Mode",
    title: "Plan every cut. Build when you're ready.",
    intro:
      "Plan Mode is non-destructive: cuts are lightweight records with a live preview. Edit, move, disable or delete them, then Build all at once. Go back to the plan as many times as you need — the original model is never modified.",
    plane: {
      title: "Plane Cut",
      body: "Drag a line across the model and a flat cut is placed through it. Select the cut in the list and use <strong>Edit Cut Surface</strong> to move, rotate or scale the plane with <kbd>G</kbd> <kbd>R</kbd> <kbd>S</kbd> — the connector follows.",
      checks: [
        "<strong>Two Contacts / Base Split</strong> — cut both feet off a base in one go, each with its own connector",
        "<strong>Chain Cuts</strong> — start the next cut automatically",
        "Connector position, rotation and scale editable per cut",
      ],
    },
    curve: {
      title: "Curve Cut",
      body: "Draw a curved line over the model and the cut follows it all the way through. Drag control points afterwards, add or remove them, or slide the whole curve; smoothing and point count are yours to set.",
      checks: [
        "Cut surface extruded along the view direction",
        "Point editor: drag, <kbd>Ctrl</kbd>+click to add, <kbd>X</kbd> to delete, <kbd>Ctrl</kbd>+<kbd>Z</kbd> undo",
      ],
    },
    freehand: {
      title: "Freehand Cut",
      body: "For everything a plane can't reach: draw a closed loop <em>around</em> the surface — a neck, a wrist, a tail — orbiting between strokes. The loop is filled and used as the cut surface.",
      checks: [
        "Orbit with <kbd>MMB</kbd> while drawing, close the loop at the start point or with <kbd>Enter</kbd>",
        "Smoothing and control-point count adjustable before and after",
      ],
    },
    build: {
      title: "Build, review, approve",
      body: "<strong>Build</strong> runs the booleans and puts the parts in an <code>ESP_Built_&lt;name&gt;</code> collection. Not happy? <strong>Back to Plan</strong> restores the draft with every cut intact. <strong>Approve</strong> finishes and, with <em>Keep Original</em>, parks the source model in a hidden backup collection.",
      checks: [
        "Untick <em>Ready</em> to leave a cut out of the build, hide its preview or delete it",
        "<strong>Skip Failed Cuts</strong> keeps building when one boolean fails",
        "Optional voxel <strong>Remesh</strong> of the built parts",
      ],
    },
  },

  quickCut: {
    eyebrow: "Quick Cut",
    title: "Or just cut it now",
    intro:
      "Quick Cut is the immediate mode: draw once and get the final parts with the connector already in place. No plan, no history — the same tools, the fastest path.",
    checks: [
      "<strong>Plane, Curve and Freehand</strong> all work in Quick Cut",
      "Automatic connector using the current shape, size and clearance",
      "Parts named by side: <code>_UPPER/_LOWER</code>, <code>_LEFT/_RIGHT</code>, <code>_FRONT/_BACK</code>",
      "Switch to Plan Mode at any time with one toggle",
    ],
  },

  connectors: {
    eyebrow: "Connectors",
    title: "Pins and sockets that fit your printer",
    intro:
      "Every cut gets a pin on one side and a matching socket on the other. Tune the fit once in the preferences and forget about it.",
    shapes: ["Cylinder", "Tapered", "Hexagon", "Box"],
    shapesCustom: "+ your own meshes",
    checks: [
      "<strong>Size presets</strong> or explicit width and height in millimetres",
      "<strong>Clearance</strong> between pin and socket, printer specific",
      "<strong>Asymmetric tip</strong> — deeper socket than pin, plus extra tip length",
      "<strong>Pin side</strong> A or B, swap with one click",
      "<strong>Manual adjust</strong> — select the connector and move, rotate or scale it freely, reset any time",
      "<strong>Cut gap (kerf)</strong> — material removed along the cut so parts don't touch",
      "<strong>Custom library</strong> — any rigid mesh in the <code>ESP_Connectors</code> collection shows up in the Shape menu",
    ],
  },

  features: {
    eyebrow: "Everything included",
    title: "Feature list",
    items: {
      plane: { title: "Plane Cut", body: "Drag a line in the viewport → flat cut through the model." },
      curve: { title: "Curve Cut", body: "Draw a curved line over the model → the cut follows it through." },
      freehand: {
        title: "Freehand Cut",
        body: "Closed loop around the surface, orbit while drawing → filled cut surface.",
      },
      baseSplit: {
        title: "Two Contacts / Base Split",
        body: "Two contacts cut as one operation, each with its own connector.",
      },
      quickCut: { title: "Quick Cut mode", body: "Immediate final parts, no history." },
      planMode: {
        title: "Plan Mode",
        body: "Non-destructive records, editable surfaces and connectors, Build / Back to Plan / Approve.",
      },
      connectors: {
        title: "Connectors",
        body: "Cylinder, Tapered, Hexagon, Box or custom meshes; presets or explicit size; clearance; asymmetric tip; pin side; manual transform.",
      },
      kerf: { title: "Cut Gap (kerf)", body: "Material removed along the cut so parts don't touch." },
      remesh: { title: "Remesh", body: "Optional voxel remesh of the built parts." },
      exploded: {
        title: "Exploded View",
        body: "Move the parts apart to inspect the connectors, collapse back.",
      },
      export: { title: "Export", body: "One file per part — STL, OBJ, FBX — to a folder, in millimetres." },
      checkMesh: { title: "Check Mesh", body: "Manifold check with a warning before cutting." },
    },
  },

  who: {
    eyebrow: "Made for",
    title: "Who is it for?",
    cards: {
      minis: {
        title: "Miniature &amp; figure makers",
        body: "Split busts and figurines at necks, wrists and bases so each part prints upright with minimal supports.",
      },
      cosplay: {
        title: "Cosplay &amp; props",
        body: "Helmets, armour and weapons bigger than the build plate — cut them into pieces that pin back together.",
      },
      product: {
        title: "Product &amp; mechanical prototyping",
        body: "Explicit millimetre sizes, clearance and kerf: parts that fit the way the CAD says they should.",
      },
      farms: {
        title: "Print farms &amp; hobbyists",
        body: "Plan a whole model once, rebuild after tweaks, export every part with one click.",
      },
    },
  },

  compat: {
    eyebrow: "Requirements",
    title: "Compatibility, performance & limits",
    compatibility: {
      title: "Compatibility",
      checks: [
        "Blender <strong>{blenderMin} – {blenderMax}</strong>, tested headless on both LTS ends in CI",
        "Windows, macOS and Linux",
        "Closed, <strong>manifold</strong> meshes with applied scale and rotation",
        "Millimetre scene (unit scale 0.001) or the <em>1 unit = 1 mm</em> preference",
      ],
    },
    performance: {
      title: "Performance",
      checks: [
        "Planning is instant: geometry only runs on <strong>Build</strong>",
        "Build time depends on polygon count and the boolean solver",
        "<em>Manifold</em> solver (Blender 4.5+) used automatically, <em>Exact</em> as fallback",
      ],
    },
    limits: {
      title: "Known limitations",
      items: [
        "Open, self-intersecting or broken meshes give wrong booleans — run <em>Check Mesh</em> first.",
        "Not a printability analyser: wall thickness, orientation, supports and tolerances are up to you.",
        "Connectors are rigid by design; no articulated or movable joints.",
        "Automatic bed-size based cut suggestions are on the roadmap, not in yet.",
      ],
    },
  },

  install: {
    eyebrow: "Installation",
    title: "Install in under a minute",
    steps: [
      "<strong>Download</strong> <code>easy_slice_print-{version}.zip</code> below.",
      "In Blender open <strong>Edit → Preferences → Add-ons</strong>, click the <strong>⌄</strong> menu in the top right and choose <strong>Install from Disk…</strong>, then pick the zip.",
      "Enable <strong>{name}</strong>.",
      "Press <kbd>N</kbd> in the 3D Viewport: the panel is in the <strong>EasySlice</strong> tab of the sidebar.",
    ],
    quickstart: {
      title: "Quick start",
      steps: [
        "Use a millimetre scene, or set <em>Preferences → EasySlice → Units → 1 unit = 1 mm</em>.",
        "Select a closed mesh, apply scale &amp; rotation (<kbd>Ctrl</kbd>+<kbd>A</kbd>). Run <em>Check Mesh</em> if unsure.",
        "Pick <strong>Quick Cut</strong> or <strong>Plan Mode</strong>, click <strong>Plane</strong>, <strong>Curve</strong> or <strong>Freehand</strong> and draw.",
        "Set the connector shape, size, pin side, cut gap and clearance.",
        "<strong>Build</strong>, check the fit in <strong>Exploded View</strong>, <strong>Export</strong>.",
      ],
      note: "Clearance is printer specific (0.15–0.4 mm typical). Test print a small piece first.",
    },
  },

  download: {
    eyebrow: "Download",
    body: "Free, no account, no license key. The zip installs straight into Blender. Source code, issues and older versions are on GitHub.",
    releases: "All releases",
    changelog: "Changelog",
    note: "Also coming to the Blender Extensions platform, so you can install it from <em>Preferences → Get Extensions</em>.",
    meta: {
      version: "Version",
      blender: "Blender",
      platforms: "Platforms",
      platformsValue: "Windows · macOS · Linux",
      license: "License",
      price: "Price",
      priceValue: "Free",
    },
  },

  faq: {
    eyebrow: "FAQ",
    title: "Questions & answers",
    items: [
      {
        q: "Is it really free?",
        a: "Yes. {name} is free software under the GNU GPL v3.0 or later: use it, study it, change it and share it, also commercially, as long as derivative works keep the same license.",
      },
      {
        q: "Which Blender versions are supported?",
        a: "Blender {blenderMin} through {blenderMax}. The test-suite runs headless on both LTS ends on every commit. Windows, macOS and Linux.",
      },
      {
        q: "Does it modify my original model?",
        a: "Not in Plan Mode. Cuts are stored as records and only run when you press <strong>Build</strong>; the source object is kept in a hidden <code>ESP_Backup</code> collection when <em>Keep Original</em> is on. <strong>Back to Plan</strong> restores the draft at any time.",
      },
      {
        q: "What clearance should I use for the connectors?",
        a: "It depends on your printer, material and slicer. 0.15–0.4 mm covers most FDM setups; resin printers can go tighter. Print a small test pair first — a tapered pin is the most forgiving shape.",
      },
      {
        q: "Can I use my own connector shapes?",
        a: "Yes. Open the connector library (icon next to <em>Shape</em>), drop any rigid mesh into the <code>ESP_Connectors</code> collection following the unit-box convention and it appears in the Shape menu.",
      },
      {
        q: "What about articulated joints or ball joints?",
        a: "Out of scope by design: connectors are rigid pins and sockets for gluing or press-fitting parts back together.",
      },
      {
        q: "My cut fails or gives a strange result.",
        a: "Boolean operations need a closed, manifold mesh with applied scale. Run <em>Check Mesh</em> first. Very dense meshes take longer; the <em>Manifold</em> solver (Blender 4.5+) is picked automatically when available. Enable <em>Skip Failed Cuts</em> to keep building the rest.",
      },
    ],
  },

  support: {
    eyebrow: "Support & roadmap",
    title: "Actively developed, in the open",
    cards: {
      bug: {
        title: "Found a bug?",
        body: "Open an issue with your Blender version and, if you can, the .blend file. Crashes and wrong cuts get priority.",
        link: "Report on GitHub →",
      },
      feature: {
        title: "Want a feature?",
        body: "Bed-size based cut suggestions are next on the list. Vote, discuss or propose your own in the tracker.",
        link: "Request a feature →",
      },
      contribute: {
        title: "Want to contribute?",
        body: "Pure-geometry core, headless tests on two Blender versions, ruff-formatted Python. Pull requests welcome.",
        link: "Read the guide →",
      },
    },
  },

  footer: {
    legal:
      "Free software under the GNU GPL v3.0 or later. {name} is an independent project: it is not affiliated with, endorsed by or derived from any commercial add-on, and no third-party code or assets are included.",
    project: {
      title: "Project",
      source: "Source code",
      releases: "Releases",
      changelog: "Changelog",
      license: "License",
    },
    docs: {
      title: "Docs",
      architecture: "Architecture",
      features: "Feature map",
      contributing: "Contributing",
      readme: "README (English)",
    },
    help: {
      title: "Help",
      bug: "Report a bug",
      feature: "Request a feature",
      discussions: "Discussions",
      security: "Security policy",
    },
    copyright:
      "© {year} {author} and {name} contributors · Blender is a trademark of the Blender Foundation.",
  },

  notFound: {
    title: "Page not found — {name}",
    code: "404",
    heading: "That page got cut off.",
    body: "Nothing here — but the connectors still fit.",
    cta: "Back to the start",
  },

  media: {
    badgeVideo: "Demo video coming soon",
    badgeImage: "Screenshot coming soon",
    hero: {
      alt: "{name} demo: plane cuts across a carousel horse's legs and a curve cut over its head, built into parts and pulled apart",
      expects: "20–40 s screen recording: draw a Freehand cut → Build → Exploded View → Export",
    },
    stepCut: {
      alt: "Viewport while drawing a cut line over the model",
      expects: "Viewport mid-draw, the cut line overlay visible",
    },
    stepConnectors: {
      alt: "Built parts in exploded view showing the pin and socket",
      expects: "Built parts in Exploded View, pin and socket visible",
    },
    stepExport: {
      alt: "Export panel with the parts written as STL files",
      expects: "Export panel with the folder and format, exported parts in the slicer",
    },
    planeCut: {
      alt: "Plane cut: dragging a line across a model in Plan Mode",
      expects: "Plan Mode: drag a Plane cut, then Edit Cut Surface and move the plane with G/R",
    },
    curveCut: {
      alt: "Curve cut: a curved line drawn over a carousel horse's tail, which comes off as its own part",
      expects: "Plan Mode: draw a Curve cut across the silhouette, drag a few control points",
    },
    freehandCut: {
      alt: "Freehand cut: drawing a closed loop around a neck while orbiting",
      expects: "Plan Mode: Freehand loop around a neck/wrist, orbiting with MMB between strokes",
    },
    buildExport: {
      alt: "Build, Back to Plan, Approve and Export",
      expects: "Build → parts appear → Back to Plan → tweak → Approve → Export STL",
    },
    quickCut: {
      alt: "Quick Cut: one plane cut with automatic connector, no history",
      expects: "Quick Cut mode: one drag, parts and connector appear immediately",
    },
    connectors: {
      alt: "Connector shapes: cylinder, tapered, hexagon, box and a custom mesh",
      expects: "Close-up of the five connector shapes side by side, pins and sockets",
    },
  },
};

export type Dict = typeof en;
export default en;
