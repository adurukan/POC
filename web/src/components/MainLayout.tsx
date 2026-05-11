import { useState } from 'react'
import type { QuestionResponse } from '../api/client'
import QuestionPanel from './QuestionPanel'
import UserAvatar from './UserAvatar'
import VisualPanel from './VisualPanel'

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
    </div>
  )
}
