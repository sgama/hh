# H. Haruna Portfolio — Hugo + Blowfish

Static rebuild of https://hharuna0606.wixsite.com/portfolio using the [Blowfish](https://blowfish.page/) Hugo theme v3 (installed as a [Hugo Module](https://gohugo.io/hugo-modules/)).

## Requirements

- [Hugo extended](https://gohugo.io/installation/) in the Blowfish-supported range (0.164–0.167; newer local versions print an advisory warning only), plus Go 1.24+ (Hugo Modules), GNU make, Node LTS (markdownlint/ESLint via `npx`) and [taplo](https://taplo.tamasfe.dev) (`brew install taplo`).
- `make media-optimize` additionally requires [pngquant](https://pngquant.org) and [jpegoptim](https://github.com/kornelski/jpegoptim) (`brew install pngquant jpegoptim`); before optimizing in place it saves an untouched copy of every file it rewrites to `originals/` (gitignored — kept locally just in case, never committed).

## Quickstart

```sh
make setup   # fetch the Blowfish theme module
make dev     # live-reload server on :1313
```

`make check` = `make lint` + strict build, run locally and in CI (`.github/workflows/ci.yml`):

- **markdownlint** — all markdown, config in `.markdownlint.jsonc`
- **ESLint** — any custom JavaScript added to this site (`eslint.config.mjs`; the theme's own bundles ship as-is upstream)
- **taplo** — TOML lint + formatting check over `config/_default/`

## Main targets

| Target           | Purpose                                                                                                                      |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `setup`          | Fetch the Blowfish theme module (host tools only)                                                                            |
| `dev`            | Local live-reload server                                                                                                     |
| `build`          | Minified production build into `public/`                                                                                     |
| `check`          | CI gate: `lint` + strict build                                                                                               |
| `lint`           | markdownlint + ESLint (custom JS) + taplo (TOML lint/format)                                                                 |
| `update`         | Bump Blowfish to the latest upstream release                                                                                 |
| `tidy`           | Reconcile `go.mod` / `go.sum`                                                                                                |
| `media-optimize` | Optimize PNG/JPEG under `content/` + `assets/` in-place (pngquant, jpegoptim); copies are saved to `originals/` (gitignored) |
| `clean`          | Remove build artifacts                                                                                                       |

Run `make help` for the full list.

## Layout

```text
config/_default/   Site + theme configuration (Hugo Modules → blowfish/v2)
content/_index.md  Homepage (headline + welcome copy, project card grid)
content/about.md   About
content/certifications.md  Certifications
content/contact.md         Contact
content/projects/  Page bundles — one directory per project, gallery under images/
assets/            Shared images (author photo, social, etc.)
```

## Deploying

Set your production URL in `config/_default/hugo.toml` (`baseURL`) and build with `make build`.

## Pending configuration

- `baseURL` — intentionally stays `http://localhost:1313/` until a production domain/host is chosen; every absolute link (sitemap, Open Graph, hreflang) derives from it at build time.
- Contact form — posts to `https://formspree.io/f/YOUR_FORM_ID`; create a form at formspree.io and replace the ID in **both** `content/contact.md` and `content/contact.ja.md`.

## Multilingual (EN / 日本語)

- English is the default language; translations use **filename suffixes** (`index.ja.md`, `about.ja.md`, …) so page bundles and their images are shared between languages.
- First visit performs a **client-side redirect to the browser's preferred language** (Japanese browsers → `/ja/`, everyone else → `/`), falling back to English. See `params.toml → [languageRedirect]`.
- Site header includes a language switcher cast automatically by Blowfish for every page pair that exists.

To add a translation of a page, create the `.ja.md` sibling (e.g. `content/projects/<slug>/index.ja.md`) with the same front matter keys translated.
