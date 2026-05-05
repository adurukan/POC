# Matemantık Web UI Kit

A React/JSX recreation of the **Matemantık** student web app. Designed against the source codebase at `POC/web/`.

This kit is a **brand-elevated** recreation: the source app uses bare cobalt-blue CSS (`#2563eb`), but the brand identity (favicon, hero illustration) is electric violet. The kit unifies on the violet identity laid out in `colors_and_type.css`.

## What's in this kit

`index.html` boots a clickable end-to-end flow:
1. **Login** — pixel-clean version of the source `LoginPage` (try `alpbek` / `1234`)
2. **App** — three-panel `MainLayout`:
   - `QuestionPanel` — subject + question dropdowns, typewriter question text
   - `VisualPanel` — embedded SVG visual
   - `SolutionPanel` — step-by-step reveal
3. **UserAvatar** dropdown with sign-out

## Components (`components/`)

| Component | Source file | Notes |
|---|---|---|
| `LoginScreen.jsx` | `POC/web/src/components/LoginPage.tsx` | Wordmark + lightning-Z logo, fields, primary CTA |
| `AppShell.jsx` | `POC/web/src/components/MainLayout.tsx` | 3-panel grid (question/visual top, solution bottom) |
| `QuestionPanel.jsx` | `POC/web/src/components/QuestionPanel.tsx` | Subject + question selects, typewriter body |
| `VisualPanel.jsx` | `POC/web/src/components/VisualPanel.tsx` | Embeds the elevator SVG |
| `SolutionPanel.jsx` | `POC/web/src/components/SolutionPanel.tsx` | "Sonraki Adım" reveals one step at a time |
| `UserAvatar.jsx` | `POC/web/src/components/UserAvatar.tsx` | Pinned top-right, dropdown logout |
| `Mock data` | `POC/api/seed.py` | First three Turkish questions reused verbatim |

## What's intentionally not real

- No backend; data is in `mockData.js`
- No real auth; any credentials log you in (the source hardcodes `alpbek`/`1234`)
- The visual panel renders a single embedded SVG (the elevator); in production it'd fetch by question
