import { useEffect, useState } from 'react'
import { getSubjects, getQuestions } from '../api/client'
import type { QuestionResponse } from '../api/client'

interface Props {
  onQuestionSelect: (question: QuestionResponse | null) => void
}

export default function QuestionPanel({ onQuestionSelect }: Props) {
  const [subjects, setSubjects] = useState<string[]>([])
  const [questions, setQuestions] = useState<QuestionResponse[]>([])
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null)
  const [displayedText, setDisplayedText] = useState('')

  useEffect(() => {
    getSubjects().then(setSubjects)
  }, [])

  useEffect(() => {
    if (!selectedQuestion) {
      setDisplayedText('')
      return
    }
    setDisplayedText('')
    let i = 0
    const text = selectedQuestion.question_text
    const interval = setInterval(() => {
      i++
      setDisplayedText(text.slice(0, i))
      if (i >= text.length) clearInterval(interval)
    }, 18)
    return () => clearInterval(interval)
  }, [selectedQuestion])

  async function handleSubjectChange(subject: string) {
    setSelectedQuestion(null)
    onQuestionSelect(null)
    if (!subject) {
      setQuestions([])
      return
    }
    const data = await getQuestions(subject)
    setQuestions(data)
  }

  function handleQuestionChange(id: string) {
    const q = questions.find((q) => q.id === Number(id)) ?? null
    setSelectedQuestion(q)
    onQuestionSelect(q)
  }

  const isTyping = selectedQuestion && displayedText.length < selectedQuestion.question_text.length

  return (
    <div className="panel-card area-question">
      <div className="panel-head">
        <span className="panel-title">Soru</span>
        <div className="selector-row">
          <select
            className="select"
            defaultValue=""
            onChange={(e) => handleSubjectChange(e.target.value)}
          >
            <option value="" disabled>Konu seçin</option>
            {subjects.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>

          {questions.length > 0 && (
            <select
              className="select"
              defaultValue=""
              onChange={(e) => handleQuestionChange(e.target.value)}
            >
              <option value="" disabled>Soru seçin</option>
              {questions.map((q) => (
                <option key={q.id} value={q.id}>Soru {q.id}</option>
              ))}
            </select>
          )}
        </div>
      </div>

      <div className="panel-body">
        {selectedQuestion
          ? <p className="q-text">
              {displayedText}
              {isTyping && <span className="caret" />}
            </p>
          : <p className="placeholder">Bir konu ve soru seçerek başlayalım.</p>
        }
      </div>
    </div>
  )
}
