# Brand DNA — falsify-eval

This file documents the visual and verbal DNA shared between
**bhardwajandsons.com** and the **falsify-eval** GitHub presence so the two
read as one house. Every contributor to either repo should keep this open.

---

## Palette

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#f3eee5` | Default background. The page is paper. |
| `--paper-warm` | `#f7f2e8` | Lighter paper for hero gradients |
| `--ink` | `#1c1611` | Body text, primary headlines |
| `--ink-mute` | `#6b5e4f` | Subheads, secondary text, captions |
| `--rule` | `#d4c8b2` | Hairlines, dividers, table borders |
| `--accent` | `#9c4a1a` | The single accent. Sienna/burnt-orange. **Use sparingly** — never on body text, never twice on the same screen. |
| `--gold` | `#9d8147` | Brass plates, kickers, Sanskrit text, version pills |

### Dark mode overrides

| Token | Hex |
|---|---|
| `--paper` | `#0e0c09` |
| `--ink` | `#f3eee5` |
| `--ink-mute` | `#a39580` |
| `--rule` | `#3a342a` |
| `--accent` | `#d8702f` |
| `--gold` | `#c9a973` |

---

## Typography

- **Display (italic) — Garamond, EB Garamond, Georgia, serif** — wordmarks, hero, page titles, big numbers
- **Body — Garamond stack, regular, 1.05–1.15rem, line-height 1.5** — prose
- **Kicker / tag — Helvetica Neue, Arial, sans-serif — 0.65rem, ALL CAPS, letter-spacing 0.2–0.3em, weight 500–600** — small labels above headlines
- **Sanskrit motif — Sanskrit Text, serif** — सत्यमेव जयते sparingly, never as decoration. Always meaningful. Always coloured `--gold`.

The page should read as a quietly typeset book. Not a startup landing page.

---

## Voice

- Calibrated, never inflated.
- Specific over abstract. Numbers over adjectives.
- "Catches", "fails", "rejects" — not "ensures", "guarantees", "boosts".
- No em-dashes when an en-dash works. No hype words ("revolutionary", "unprecedented", "best-in-class").
- Sanskrit terms in IAST when used in prose (e.g., *Saptāṅga*, *kośa-discipline*).
- Public credit by name when an external person finds something. Always.
- Hard own-up when something is wrong. No spin.

---

## Component tokens (carry between repos)

```
border-radius: 2px           /* paper, not plastic */
hairline:      1px solid var(--rule)
shadow:        none          /* paper has no shadow */
button:        flat, brand-accent fill, white text, uppercase letter-spaced 0.2em, 0.85rem 1.4rem
table:         hairline borders only, no fills, monospace allowed for verdicts
```

---

## Mermaid theme

For any Mermaid diagram in this repo, use this header so the diagram
matches the brand palette:

```
%%{init: {'theme': 'base', 'themeVariables': {
    'fontFamily': 'Garamond, EB Garamond, Georgia, serif',
    'primaryColor': '#f3eee5',
    'primaryTextColor': '#1c1611',
    'primaryBorderColor': '#9c4a1a',
    'lineColor': '#9d8147',
    'tertiaryColor': '#faf6ed',
    'tertiaryBorderColor': '#d4c8b2',
    'edgeLabelBackground': '#f3eee5'
}}}%%
```

Status classDefs to reuse:

```
classDef ok    fill:#eef3e8,stroke:#3d7a4a,color:#1a3d22;
classDef fail  fill:#f7e9e3,stroke:#9c4a1a,color:#5a1c0c;
classDef novel fill:#fef9e7,stroke:#9d8147,color:#5a4720,stroke-width:2px;
classDef gate  fill:#f3eee5,stroke:#1c1611,color:#1c1611,stroke-width:2px;
```

---

## Marks

The four-null mark — four squares, decreasing opacity (1.00, 0.72, 0.46, 0.22) — represents the four nulls A, B, C, D. Use the existing SVGs:

- `assets/hero-light.svg` / `assets/hero-dark.svg` — README hero
- `assets/social-preview.svg` / `.png` — GitHub social preview (1280 × 640)

Do not alter the proportions. The four-square cadence is the brand mark.

---

## Cross-repo links to keep in sync

Whenever the brand site or this repo changes one of these, the other should
match within the same day:

| Surface | brand site | falsify-eval |
|---|---|---|
| Tagline | "A house of standards" | README hero · social preview |
| Headline phrase | *Calibrated falsification harness for retrieval evaluation* | README sub-hero |
| Sanskrit motif placement | footer | 404 · social preview · issue templates |
| Accent colour | `#9c4a1a` | `#9c4a1a` |
| Dark-mode accent | `#d8702f` | `#d8702f` |

When this file changes, update both surfaces in the same session. Drift here
is a calibration failure.
