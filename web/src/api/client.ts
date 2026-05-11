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

// ---------- Teacher Studio ----------

export interface TeacherSubjectOption {
  slug: string
  title: string
  subject: string | null
  grade: string | null
}

export interface PendingQuestion {
  request_id: string
  grade: string
  subject: string
  topic: string
  question_text: string | null
  solution_steps: SolutionStep[]
  visual_path: string | null
}

async function postJson<T>(path: string, body: unknown): Promise<T | null> {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (res.status === 204) return null
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail?.detail ?? `Request failed: ${path}`)
  }
  return res.json() as Promise<T>
}

async function getJson<T>(path: string): Promise<T | null> {
  const res = await fetch(path)
  if (res.status === 204) return null
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail?.detail ?? `Request failed: ${path}`)
  }
  return res.json() as Promise<T>
}

export async function teacherLogin(
  username: string,
  password: string,
): Promise<{ ok: boolean; username: string }> {
  const res = await postJson<{ ok: boolean; username: string }>(
    '/api/auth/teacher/login',
    { username, password },
  )
  if (!res) throw new Error('Login response empty.')
  return res
}

export async function teacherSubjects(grade = '5'): Promise<TeacherSubjectOption[]> {
  const res = await fetch(`/api/teacher/subjects?grade=${encodeURIComponent(grade)}`)
  if (!res.ok) throw new Error('Failed to fetch teacher subjects')
  return res.json()
}

export async function teacherNext(
  grade: string,
  subject: string,
): Promise<PendingQuestion | null> {
  return getJson<PendingQuestion>(
    `/api/teacher/next?grade=${encodeURIComponent(grade)}&subject=${encodeURIComponent(subject)}`,
  )
}

export async function teacherFeedback(body: {
  request_id: string
  feedback: string
}): Promise<PendingQuestion | null> {
  return postJson<PendingQuestion>('/api/teacher/feedback', body)
}

export async function teacherAccept(body: {
  request_id: string
}): Promise<PendingQuestion | null> {
  return postJson<PendingQuestion>('/api/teacher/accept', body)
}

export async function teacherReject(body: {
  request_id: string
  comment: string
}): Promise<PendingQuestion | null> {
  return postJson<PendingQuestion>('/api/teacher/reject', body)
}
