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
    <div className="panel">
      <div className="panel-body">
        {svgContent
          ? <div dangerouslySetInnerHTML={{ __html: svgContent }} />
          : <p className="placeholder">No visual available for this question.</p>
        }
      </div>
    </div>
  )
}
