import { useEffect, useState } from 'react'
import type { QuestionResponse } from '../api/client'

interface Props {
  /** Student mode: shows SVG or HTML from a saved question's visual_path. */
  question?: QuestionResponse | null
  /** Teacher mode: render this HTML string directly via iframe srcDoc. */
  htmlSrcDoc?: string | null
  /** Teacher/student mode: iframe src URL (e.g. "/api/visuals/teacher/...html"). */
  htmlUrl?: string | null
  /** Override the panel title (defaults to "Oyun"). */
  title?: string
}

function isHtmlPath(path: string | null | undefined): boolean {
  return !!path && /\.html?$/i.test(path)
}

export default function VisualPanel({ question, htmlSrcDoc, htmlUrl, title }: Props) {
  const [svgContent, setSvgContent] = useState<string | null>(null)

  // Resolve which source to render. Explicit teacher-mode props win.
  const directSrc = htmlSrcDoc ?? null
  const explicitUrl = htmlUrl ?? null
  const studentHtmlUrl =
    !directSrc && !explicitUrl && question && isHtmlPath(question.visual_path)
      ? `/api/visuals/${question.visual_path}`
      : null
  const studentSvgQuestion =
    !directSrc && !explicitUrl && question && !isHtmlPath(question.visual_path)
      ? question
      : null

  useEffect(() => {
    if (!studentSvgQuestion || !studentSvgQuestion.visual_path) {
      setSvgContent(null)
      return
    }
    fetch(`/api/questions/${studentSvgQuestion.id}/visual`)
      .then((res) => res.text())
      .then(setSvgContent)
      .catch(() => setSvgContent(null))
  }, [studentSvgQuestion])

  const hasAnyVisual = !!(directSrc || explicitUrl || studentHtmlUrl || svgContent)

  return (
    <div className="panel-card area-visual visual-panel-card">
      <div className="panel-head">
        <span className="panel-title">{title ?? 'Oyun'}</span>
        <span className="panel-eyebrow">
          {directSrc || explicitUrl || studentHtmlUrl ? 'HTML' : svgContent ? 'SVG' : ''}
        </span>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        <div className="visual-canvas">
          {directSrc ? (
            <iframe
              title="game"
              srcDoc={directSrc}
              sandbox="allow-scripts"
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          ) : explicitUrl || studentHtmlUrl ? (
            <iframe
              title="game"
              src={(explicitUrl ?? studentHtmlUrl) as string}
              sandbox="allow-scripts"
              style={{ width: '100%', height: '100%', border: 'none' }}
            />
          ) : svgContent ? (
            <div dangerouslySetInnerHTML={{ __html: svgContent }} />
          ) : (
            <p className="placeholder" style={{ padding: 24 }}>
              {hasAnyVisual ? '' : question ? 'Bu soru için görsel yok.' : 'Henüz görsel yok.'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
