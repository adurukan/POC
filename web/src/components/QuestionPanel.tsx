import { useEffect, useState } from 'react'
import { getQuestions, getSubjects } from '../api/client'
import type { QuestionResponse } from '../api/client'
import LessonPanel from './LessonPanel'

interface Props {
  onQuestionSelect: (question: QuestionResponse | null) => void
}

export default function QuestionPanel({ onQuestionSelect }: Props) {
  const [subjects, setSubjects] = useState<string[]>([])
  const [questions, setQuestions] = useState<QuestionResponse[]>([])
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null)

  useEffect(() => {
    getSubjects().then(setSubjects)
  }, [])

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

  if (!selectedQuestion) {
    return (
      <div className="panel-card area-question">
        <div className="panel-head">
          <span className="panel-title">Soru</span>
          <div className="selector-row">
            <select
              className="select select-fixed-subject"
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
                className="select select-fixed-question"
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
          <p className="placeholder">Bir konu ve soru seçerek başlayalım.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="area-question" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="selector-row" style={{ display: 'flex', gap: 8 }}>
        <select
          className="select select-fixed-subject"
          value={selectedQuestion.subject_name}
          onChange={(e) => handleSubjectChange(e.target.value)}
        >
          <option value="" disabled>Konu seçin</option>
          {subjects.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        {questions.length > 0 && (
          <select
            className="select select-fixed-question"
            value={selectedQuestion.id}
            onChange={(e) => handleQuestionChange(e.target.value)}
          >
            {questions.map((q) => (
              <option key={q.id} value={q.id}>Soru {q.id}</option>
            ))}
          </select>
        )}
      </div>

      <LessonPanel
        question={selectedQuestion.question_text}
        steps={selectedQuestion.solution_steps}
      />
    </div>
  )
}
