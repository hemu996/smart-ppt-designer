# Smart PPT Studio（PPT 设计台）

A DSH plugin that gives the legacy **smart-ppt-designer** skill package a real
left-sidebar entry in the Harness Web UI.

## What it does

- Adds a **PPT 设计台** row to `sidebar.panellist` and a matching keyed `main`
  panel, so the studio is one click away from the sidebar.
- Embeds the legacy package's `assets/style-index.json` (19 visual systems:
  5 built-in + 14 extracted from reference decks) as a searchable style browser
  with light/dark and built-in/extracted filters.
- Surfaces the legacy spec's **28 hard red lines**, **13-step workflow** and
  **standard scripts** as quick-reference tabs.
- Composes a generation prompt that carries the selected visual system and a
  written `style_rationale`, then calls the `smart-ppt-designer` skill. This is
  what "结合旧版" means: it does not reimplement PPTX generation, it drives the
  old skill through its own contracts.

## v1.5.0 — Premium refresh

The sidebar UI was upgraded to a higher-end design language while keeping every
feature intact.

- **Visual overhaul** — brand mark + gradient title, hairline divider, card
  hover lift / shadow, refined chips, buttons and detail panel. All colors use
  `--dsw-alias-*` theme tokens, so the panel follows the system light/dark mode
  automatically (no dark-background by default, per the bright-background
  preference).
- **Favorites** — star any style or template card; the set persists to
  `localStorage` (`spps.favorites.v1`) and a pinned banner summarizes the count.
  No server, no telemetry.
- **Send to conversation** — the prompt panel now has two actions: "发送到对话"
  (best-effort: fills the current DSH composer input via
  `[data-composer-card]` and dispatches an `input` event; fails open to clipboard
  copy if the composer is not found) and "复制生成指令" (clipboard copy).
- Data is still read-only: the plugin only browses, checks and composes prompts;
  it never writes back to the skill package.

## Source of the embedded data

`data/styles.json` is a lossless compact copy of the `style-index.json` inside
yesterday's `smart-ppt-designer.zip` (v5.6). The rules, workflow and command
text are transcribed from that package's `SKILL.md`. Nothing is written back to
the skill package.

## Layout

```
smart-ppt-studio/
├── package.json          bundle manifest, Client module and display exports
├── cordis.patch.yml      inserts the plugin row
├── index.js              Host half (anchor only)
├── client.js             Client half: sidebar row + main panel + embedded data
├── data/styles.json      18-style library copy
├── locale/en.json        Plugin Manager metadata + English UI dictionary
├── locale/zh.json        Plugin Manager metadata + Chinese UI dictionary
├── icon.svg              original artwork
└── README.md
```

## Design notes

- The Client module registers a lazy factory whose id equals the package name,
  resolving React from the browser module table. No Harness Client UI package is
  imported as a module.
- All containers, borders, labels and controls use `--dsw-alias-*` theme tokens;
  the only literal colors are the style swatches (artwork/data) and the icon.
- Resources (locale dictionaries, slot registrations) are registered inside
  `apply` and disposed on unload.
- The panel is a pure view: switching tabs, filtering and copying a prompt are
  user-only interactions, so no agent tool is exposed for them.
