/**
 * Render a p5.js sketch into a complete HTML document for iframe srcDoc.
 *
 * The backend writes the same document to disk on successful generation (see
 * agents/workflows/game_agent/render.py). The frontend duplicates the template
 * only because in-progress (pre-Accept) artifacts may not be on disk yet, or
 * the teacher may want to preview without round-tripping through the file.
 *
 * If a discrepancy ever shows up between the two templates, the backend wins.
 */
const P5_CDN = 'https://cdn.jsdelivr.net/npm/p5@1.11.0/lib/p5.min.js'

export function renderGameHtml(p5Sketch: string): string {
  return `<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <title>game</title>
  <style>
    html, body { margin: 0; padding: 0; background: #fff; }
    body { display: flex; align-items: center; justify-content: center; min-height: 100vh; }
  </style>
  <script src="${P5_CDN}"></script>
</head>
<body>
<script>
${p5Sketch}
</script>
</body>
</html>`
}
