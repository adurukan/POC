import { useState } from 'react'
import type { QuestionResponse } from '../api/client'
import QuestionPanel from './QuestionPanel'
import VisualPanel from './VisualPanel'
import SolutionPanel from './SolutionPanel'
import UserAvatar from './UserAvatar'

type Lang = 'tr' | 'en'

interface Props {
  username: string
  onLogout: () => void
  lang: Lang
  onLangChange: (next: Lang) => void
}

export default function MainLayout({ username, onLogout, lang, onLangChange }: Props) {
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null)

  return (
    <div className="app-shell">
      <UserAvatar username={username} onLogout={onLogout} lang={lang} onLangChange={onLangChange} />
      <QuestionPanel onQuestionSelect={setSelectedQuestion} />
      <VisualPanel question={selectedQuestion} />
      <SolutionPanel question={selectedQuestion} />
    </div>
  )
}
