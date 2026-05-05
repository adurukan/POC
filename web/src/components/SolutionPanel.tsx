import { useEffect, useState } from 'react'
import type { QuestionResponse, SolutionStep } from '../api/client'

interface Props {
  question: QuestionResponse | null
}

export default function SolutionPanel({ question }: Props) {
  const [steps, setSteps] = useState<SolutionStep[]>([])
  const [revealed, setRevealed] = useState(0)

  useEffect(() => {
    setSteps(question?.solution_steps ?? [])
    setRevealed(0)
  }, [question])

  const allRevealed = revealed >= steps.length

  return (
    <div className="panel-card area-solution">
      <div className="panel-head">
        <span className="panel-title">Çözüm</span>
        <span className="panel-eyebrow">{revealed} / {steps.length || '—'}</span>
      </div>
      <div className="panel-body">
        {steps.length === 0
          ? <p className="placeholder">Adımları görmek için bir soru seçin.</p>
          : <div className="step-list">
              {steps.slice(0, revealed).map((step, i) => (
                <div key={i} className={`step${i < revealed - 1 ? ' done' : ''}`}>
                  <span className="num">{i + 1}</span>
                  <span className="desc">{step.description}</span>
                  <span className="expr">{step.expression}</span>
                </div>
              ))}
            </div>
        }
      </div>
      <div className="panel-foot">
        <span style={{ fontSize: 12, color: 'var(--fg-3)' }}>
          {steps.length > 0
            ? (allRevealed ? 'Tüm adımlar gösterildi.' : 'Hazır olduğunda devam edin.')
            : ''}
        </span>
        <button
          className="btn btn-primary"
          onClick={() => setRevealed((r) => r + 1)}
          disabled={allRevealed || steps.length === 0}
        >
          {allRevealed ? 'Tamamlandı' : 'Sonraki Adım'}
        </button>
      </div>
    </div>
  )
}
