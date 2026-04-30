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

  return (
    <div className="panel">
      <div className="panel-header">
        <select defaultValue="" onChange={(e) => handleSubjectChange(e.target.value)}>
          <option value="" disabled>Select subject</option>
          {subjects.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>

        {questions.length > 0 && (
          <select defaultValue="" onChange={(e) => handleQuestionChange(e.target.value)}>
            <option value="" disabled>Select question</option>
            {questions.map((q) => (
              <option key={q.id} value={q.id}>Question {q.id}</option>
            ))}
          </select>
        )}
      </div>

      <div className="panel-body">
        {selectedQuestion
          ? <p>{displayedText}</p>
          : <p className="placeholder">Select a subject and question to begin.</p>
        }
      </div>
    </div>
  )
}
