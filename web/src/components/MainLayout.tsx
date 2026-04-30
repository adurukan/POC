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
    <div className="layout">
      <UserAvatar username={username} onLogout={onLogout} />
      <div className="layout-question">
        <QuestionPanel onQuestionSelect={setSelectedQuestion} />
      </div>
      <div className="layout-visual">
        <VisualPanel question={selectedQuestion} />
      </div>
      <div className="layout-solution">
        <SolutionPanel question={selectedQuestion} />
      </div>
    </div>
  )
}
