# Image provenance

Packs may reference images. Because the content here is published under CC BY 4.0,
**every image that ships in this repo must be redistributable** — your own work,
public domain, or a Creative Commons / equivalently-licensed image whose attribution
is recorded on the item (`illustration.credit` + `illustration.creditUrl`).

Do **not** commit scraped photos, press/agency images, or portraits of people whose
rights you don't hold. A pack renders fine text-only; when an image's rights are
unclear, ship without it.

## How images flow (current)

- **Open repo (this repo):** pack items carry `illustration.credit` +
  `illustration.creditUrl` but **no bundled `.jpg`** — it ships zero stock-photo
  binaries (clean single-license story). `build-serving` re-attaches each image's
  URL from `image-manifest.json` at build time.
- **Cache-of-record:** every photo is cached to **Cloudflare R2** (`cdn.recurxive.com`,
  see `r2.config.json` + `scripts/cache-images.mjs`), so the app always serves from
  our CDN and is immune to source link-rot. `image-manifest.json` is the ledger
  (packId → itemId → { R2 key, credit, sourceUrl, checksum, sourceStatus }).
- **First-party assets** (SVG diagrams, `.webp` scrapbook posters, PNG maps) are
  bundled in-repo under each pack folder.

## What counts

| Kind | Rule |
|---|---|
| Your own images / diagrams | Fine — released under CC BY 4.0 with the pack. |
| AI-generated diagrams (SVG) | Fine to include; note the tool in the item if relevant. |
| Public-domain images | Fine — record the source. |
| CC / openly-licensed photos | Fine **with** `credit` + `creditUrl` on the item, honoring the image's own terms. |
| Scraped / press / unlicensed photos | **Not allowed.** Omit, or replace with a licensed/PD alternative. |

## The re-sourcing pipeline (2026-07-09)

The early packs' original photos had **unrecoverable provenance** (a legacy tool
that saved no per-image source). They were all re-sourced from scratch:

1. **Stock-first cascade** (`scripts/…/resource-images.mjs`): **Pexels → Unsplash →
   Openverse → Wikimedia Commons** — all commercial-safe, each recording `credit` +
   `creditUrl` to the exact source photo. Historical packs lead with Wikimedia; nature
   packs lead with stock. Providers return candidate **lists**.
2. **Global dedup** — once an image is used on a card it is never reused on another
   (adjacent feed cards must not share an image).
3. **AI fallback** — only when *no* stock match exists does an item get a
   `gpt-image-1` image, credited `AI-generated (gpt-image-1)`.
4. **Vision QC** — a workflow of agents *looks at* each fetched CC image and flags
   off-topic/low-quality results (Openverse/Wikimedia are noisy); flagged items are
   re-fetched Pexels/Unsplash-only. This kept authentic archival photos while
   replacing junk (a kitchen for "hotel reception", a seed-catalog for "soil test").

**Result:** 0 uncredited photos across all active packs; the mix is dominated by real
stock (Pexels-heavy) plus a handful of AI-generated where stock had no match.

## The attribution gate

`tools/validate.ts` fails (and blocks CI) if any image under `generated/` lacks a
`credit`. Combined with the fetch pipeline always recording `credit`, nothing ships
unattributed again.

## Before making a pack (or this repo) public

- [ ] Every referenced image is your own, public domain, or CC/openly licensed.
- [ ] Each photo has `illustration.credit` + `illustration.creditUrl`.
- [ ] No scraped/press/unlicensed photos remain.
- [ ] No image reused across multiple cards (unless intentional).
- [ ] `npm run validate` passes (schema + attribution gate).
