import { useState } from 'react'
import type { QuestionResponse } from '../api/client'
import QuestionPanel from './QuestionPanel'
import VisualPanel from './VisualPanel'
import SolutionPanel from './SolutionPanel'
import UserAvatar from './UserAvatar'

interface Props {
  username: string
  onLogout: () => void
}

export default function MainLayout({ username, onLogout }: Props) {
  const [selectedQuestion, setSelectedQuestion] = useState<QuestionResponse | null>(null)

  return (
    <div className="app-shell">
      <UserAvatar username={username} onLogout={onLogout} />
      <QuestionPanel onQuestionSelect={setSelectedQuestion} />
      <VisualPanel question={selectedQuestion} />
      <SolutionPanel question={selectedQuestion} />
    </div>
  )
}
