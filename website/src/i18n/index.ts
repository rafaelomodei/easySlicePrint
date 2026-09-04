/**
 * Tiny i18n layer for the site.
 *
 * Routing (see `src/pages/[...lang].astro`):
 *   /            → English (default locale, no prefix)
 *   /pt/         → Português
 *   /es/         → Español
 *
 * The default-locale page carries a small inline script (see `Base.astro`)
 * that redirects first-time visitors to the locale matching their browser,
 * and remembers the language once the visitor picks one from the header.
 */
import { site } from "../data/site";
import { media, type MediaSlot } from "../data/media";
import en, { type Dict } from "./en";
import pt from "./pt";
import es from "./es";

export const languages = ["en", "pt", "es"] as const;
export type Lang = (typeof languages)[number];

export const defaultLang: Lang = "en";

/** BCP-47 tags used in `<html lang>`, `hreflang` and `og:locale`. */
export const htmlLang: Record<Lang, string> = {
  en: "en",
  pt: "pt-BR",
  es: "es",
};

const dictionaries: Record<Lang, Dict> = { en, pt, es };

/** Values substituted into `{placeholders}` found anywhere in a dictionary. */
const vars: Record<string, string> = {
  name: site.name,
  version: site.version,
  blenderMin: site.blenderMin,
  blenderMax: site.blenderMax,
  license: site.license,
  author: site.author,
  extensionUrl: site.links.blenderExtension,
  year: String(new Date().getFullYear()),
};

function fill<T>(value: T): T {
  if (typeof value === "string") {
    return value.replace(/\{(\w+)\}/g, (match, key: string) => vars[key] ?? match) as T;
  }
  if (Array.isArray(value)) return value.map((item) => fill(item)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, fill(item)])) as T;
  }
  return value;
}

const resolved = {} as Record<Lang, Dict>;

/** The dictionary for `lang`, with every `{placeholder}` already substituted. */
export function useTranslations(lang: Lang): Dict {
  return (resolved[lang] ??= fill(dictionaries[lang]));
}

/** `true` for a value that is one of the supported languages. */
export function isLang(value: unknown): value is Lang {
  return typeof value === "string" && (languages as readonly string[]).includes(value);
}

const base = import.meta.env.BASE_URL.replace(/\/$/, "");

/** Site-root-relative URL of `lang`'s home page, honouring the deploy base path. */
export function localeUrl(lang: Lang): string {
  return lang === defaultLang ? `${base}/` : `${base}/${lang}/`;
}

/** `{ en: "/…/", pt: "/…/pt/", es: "/…/es/" }` — used by the auto-detect script. */
export const localeUrls = Object.fromEntries(languages.map((lang) => [lang, localeUrl(lang)])) as Record<
  Lang,
  string
>;

/** In-page anchors of the header nav; the labels come from `t.nav`. */
export const navSections = [
  { href: "#workflow", key: "workflow" },
  { href: "#plan-mode", key: "planMode" },
  { href: "#connectors", key: "connectors" },
  { href: "#features", key: "features" },
  { href: "#install", key: "install" },
  { href: "#faq", key: "faq" },
] as const satisfies readonly { href: string; key: keyof Dict["nav"] }[];

export type MediaKey = keyof typeof media;

/** Merges `src/data/media.ts` (what to show) with the translated alt / shot text. */
export function localizedMedia(t: Dict): Record<MediaKey, MediaSlot> {
  const entries = (Object.keys(media) as MediaKey[]).map((key) => {
    const source = media[key];
    const copy = t.media[key];
    return [key, { ...source, alt: copy.alt, ...(source.placeholder ? { expects: copy.expects } : {}) }];
  });
  return Object.fromEntries(entries) as Record<MediaKey, MediaSlot>;
}
