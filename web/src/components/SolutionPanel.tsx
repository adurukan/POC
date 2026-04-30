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
    <div className="panel solution-panel">
      <div className="panel-body">
        {steps.slice(0, revealed).map((step, i) => (
          <div key={i} className="solution-step">
            <span className="step-description">{step.description}</span>
            <span className="step-expression">{step.expression}</span>
          </div>
        ))}
        {steps.length === 0 && (
          <p className="placeholder">Select a question to see solution steps.</p>
        )}
      </div>
      <div className="panel-footer">
        <button
          onClick={() => setRevealed((r) => r + 1)}
          disabled={allRevealed || steps.length === 0}
        >
          {allRevealed ? 'All steps shown' : 'Next Step'}
        </button>
      </div>
    </div>
  )
}
