import { useEffect, useState } from 'react'
import type { SolutionStep } from '../api/client'

interface Props {
  question: string
  steps: SolutionStep[]
  /** Optional override (default: "Soru") */
  title?: string
  /** When true, all solution steps render immediately (no click-to-reveal). */
  stepsRevealed?: boolean
}

export default function LessonPanel({
  question,
  steps,
  title,
  stepsRevealed = false,
}: Props) {
  const [displayedText, setDisplayedText] = useState('')
  const [revealed, setRevealed] = useState(stepsRevealed ? steps.length : 0)

  // Typewriter for the question text. Resets whenever the input changes.
  useEffect(() => {
    if (!question) {
      setDisplayedText('')
      return
    }
    setDisplayedText('')
    let i = 0
    const interval = setInterval(() => {
      i++
      setDisplayedText(question.slice(0, i))
      if (i >= question.length) clearInterval(interval)
    }, 18)
    return () => clearInterval(interval)
  }, [question])

  // Reset revealed step count whenever the question changes.
  useEffect(() => {
    setRevealed(stepsRevealed ? steps.length : 0)
  }, [question, steps, stepsRevealed])

  const isTyping = !!question && displayedText.length < question.length
  const allRevealed = revealed >= steps.length

  return (
    <div className="panel-card lesson-panel-card">
      <div className="panel-head">
        <span className="panel-title">{title ?? 'Soru'}</span>
        <span className="panel-eyebrow">
          {steps.length > 0 ? `${Math.min(revealed, steps.length)} / ${steps.length}` : ''}
        </span>
      </div>

      <div className="panel-body">
        {question ? (
          <p className="q-text">
            {displayedText}
            {isTyping && <span className="caret" />}
          </p>
        ) : (
          <p className="placeholder">Soru yükleniyor…</p>
        )}

        {steps.length > 0 && (
          <>
            <hr className="lesson-divider" />
            <div className="step-list">
              {steps.slice(0, revealed).map((step, i) => (
                <div key={i} className={`step${i < revealed - 1 ? ' done' : ''}`}>
                  <span className="num">{i + 1}</span>
                  <span className="desc">{step.description}</span>
                  <span className="expr">{step.expression}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {steps.length > 0 && !stepsRevealed && (
        <div className="panel-foot">
          <span style={{ fontSize: 12, color: 'var(--fg-3)' }}>
            {allRevealed ? 'Tüm adımlar gösterildi.' : 'Hazır olduğunda devam edin.'}
          </span>
          <button
            className="btn btn-primary"
            onClick={() => setRevealed((r) => r + 1)}
            disabled={allRevealed || isTyping}
          >
            {allRevealed ? 'Tamamlandı' : 'Sonraki Adım'}
          </button>
        </div>
      )}
    </div>
  )
}
