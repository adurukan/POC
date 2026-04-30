export interface SolutionStep {
  description: string
  expression: string
}

export interface QuestionResponse {
  id: number
  subject_name: string
  question_text: string
  solution_steps: SolutionStep[]
  visual_path: string | null
}

export async function getSubjects(): Promise<string[]> {
  const res = await fetch('/api/questions/subjects')
  if (!res.ok) throw new Error('Failed to fetch subjects')
  return res.json()
}

export async function getQuestions(subject: string): Promise<QuestionResponse[]> {
  const res = await fetch(`/api/questions?subject=${encodeURIComponent(subject)}`)
  if (!res.ok) throw new Error('Failed to fetch questions')
  return res.json()
}
