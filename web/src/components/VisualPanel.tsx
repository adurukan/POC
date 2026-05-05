import { useEffect, useState } from 'react'
import type { QuestionResponse } from '../api/client'

interface Props {
  question: QuestionResponse | null
}

export default function VisualPanel({ question }: Props) {
  const [svgContent, setSvgContent] = useState<string | null>(null)

  useEffect(() => {
    if (!question || !question.visual_path) {
      setSvgContent(null)
      return
    }
    fetch(`/api/questions/${question.id}/visual`)
      .then((res) => res.text())
      .then(setSvgContent)
      .catch(() => setSvgContent(null))
  }, [question])

  return (
    <div className="panel-card area-visual">
      <div className="panel-head">
        <span className="panel-title">Görsel</span>
        <span className="panel-eyebrow">SVG</span>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        <div className="visual-canvas">
          {svgContent
            ? <div dangerouslySetInnerHTML={{ __html: svgContent }} />
            : <p className="placeholder" style={{ padding: 24 }}>
                {question ? 'Bu soru için görsel yok.' : 'Bir soru seçildiğinde burada görselleştireceğiz.'}
              </p>
          }
        </div>
      </div>
    </div>
  )
}
