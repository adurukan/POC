import { useCallback, useEffect, useState } from 'react'
import {
  teacherAccept,
  teacherFeedback,
  teacherNext,
  teacherReject,
  teacherSubjects,
} from '../api/client'
import type { PendingQuestion, TeacherSubjectOption } from '../api/client'
import LessonPanel from './LessonPanel'
import UserAvatar from './UserAvatar'
import VisualPanel from './VisualPanel'

type Lang = 'tr' | 'en'

interface Props {
  username: string
  onLogout: () => void
  lang: Lang
  onLangChange: (next: Lang) => void
}

const GRADES = ['5']

export default function TeacherStudio({ username, onLogout, lang, onLangChange }: Props) {
  const [subjects, setSubjects] = useState<TeacherSubjectOption[]>([])
  const [grade, setGrade] = useState<string>('5')
  const [subject, setSubject] = useState<string>('')
  const [current, setCurrent] = useState<PendingQuestion | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [errorMsg, setErrorMsg] = useState<string>('')
  const [feedbackText, setFeedbackText] = useState('')
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectComment, setRejectComment] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // Load subjects on mount / grade change.
  useEffect(() => {
    teacherSubjects(grade)
      .then((opts) => {
        setSubjects(opts)
        if (opts.length > 0) {
          // `title` is the topic-level name ("Kesirler", "Geometrik Nicelikler"),
          // which is what we store in pending_questions.subject and what teachers/students
          // see in their dropdowns. The pack's `subject` column is the discipline
          // ("Matematik") and is the same for every grade-5 row, so we don't use it here.
          const first = opts[0].title
          setSubject((prev) => prev || first)
        }
      })
      .catch((e) => setErrorMsg((e as Error).message))
  }, [grade])

  const fetchNext = useCallback(async () => {
    if (!subject) return
    setLoading(true)
    setErrorMsg('')
    setFeedbackText('')
    try {
      const row = await teacherNext(grade, subject)
      setCurrent(row)
    } catch (e) {
      setErrorMsg((e as Error).message)
      setCurrent(null)
    } finally {
      setLoading(false)
    }
  }, [grade, subject])

  // Pull whenever (grade, subject) changes.
  useEffect(() => {
    if (subject) fetchNext()
  }, [grade, subject, fetchNext])

  // Helpers that consume the next-pending row returned by Accept/Reject/Feedback.
  function applyReturned(row: PendingQuestion | null) {
    setCurrent(row)
    setFeedbackText('')
  }

  async function handleSendFeedback() {
    if (!current || !feedbackText.trim()) return
    setSubmitting(true)
    setErrorMsg('')
    try {
      const next = await teacherFeedback({
        request_id: current.request_id,
        feedback: feedbackText,
      })
      applyReturned(next)
    } catch (e) {
      setErrorMsg((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleAccept() {
    if (!current) return
    setSubmitting(true)
    setErrorMsg('')
    try {
      const next = await teacherAccept({ request_id: current.request_id })
      applyReturned(next)
    } catch (e) {
      setErrorMsg((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRejectSubmit() {
    if (!current || !rejectComment.trim()) return
    setSubmitting(true)
    setErrorMsg('')
    try {
      const next = await teacherReject({
        request_id: current.request_id,
        comment: rejectComment,
      })
      setRejectOpen(false)
      setRejectComment('')
      applyReturned(next)
    } catch (e) {
      setErrorMsg((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  const canAct = !!current && !submitting
  const visualUrl = current?.visual_path ? `/api/visuals/${current.visual_path}` : null

  return (
    <div className="app-shell" style={{ display: 'block' }}>
      <UserAvatar
        username={username}
        onLogout={onLogout}
        lang={lang}
        onLangChange={onLangChange}
      />

      <div>
        {/* Top selector bar */}
        <div
          className="teacher-topbar"
          style={{
            display: 'flex',
            gap: 12,
            alignItems: 'center',
            padding: '12px 16px',
            borderBottom: '1px solid var(--ink-100)',
            background: 'var(--bg-card)',
          }}
        >
          <label style={{ fontSize: 12, color: 'var(--fg-3)' }}>Sınıf</label>
          <select
            className="select select-fixed-grade"
            value={grade}
            onChange={(e) => setGrade(e.target.value)}
          >
            {GRADES.map((g) => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>

          <label style={{ fontSize: 12, color: 'var(--fg-3)', marginLeft: 16 }}>Konu</label>
          <select
            className="select select-fixed-subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            disabled={subjects.length === 0}
          >
            {subjects.length === 0 && <option value="">— yükleniyor —</option>}
            {subjects.map((s) => (
              <option key={s.slug} value={s.title}>
                {s.title}
              </option>
            ))}
          </select>

          <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--fg-3)' }}>
            {current && (
              <code style={{ fontFamily: 'var(--font-mono)' }}>{current.request_id}</code>
            )}
          </div>
        </div>

        {loading ? (
          <div style={{ padding: 32, textAlign: 'center', color: 'var(--fg-3)' }}>
            Kuyruğa bakılıyor…
          </div>
        ) : !current ? (
          <EmptyQueue onRefresh={fetchNext} />
        ) : (
          <div
            className={`teacher-main-grid${visualUrl ? ' has-visual' : ''}`}
          >
            <LessonPanel
              question={current.question_text ?? ''}
              steps={current.solution_steps ?? []}
              title="Soru"
            />

            {visualUrl && (
              <VisualPanel htmlUrl={visualUrl} title="Oyun" />
            )}

            {/* Feedback strip + action buttons, spans full width */}
            <div className="panel-card" style={{ gridColumn: '1 / -1' }}>
              <div className="panel-head">
                <span className="panel-title">Geri bildirim</span>
              </div>
              <div className="panel-body" style={{ display: 'flex', gap: 12 }}>
                <textarea
                  className="input"
                  rows={3}
                  style={{ flex: 1, resize: 'vertical' }}
                  placeholder="Soruda, çözümde veya oyunda düzeltilmesini istediğin şeyi yaz…"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  disabled={!canAct}
                />
                <button
                  className="btn btn-primary"
                  onClick={handleSendFeedback}
                  disabled={!canAct || !feedbackText.trim()}
                  style={{ alignSelf: 'flex-end' }}
                >
                  Gönder
                </button>
              </div>
              <div
                className="panel-foot"
                style={{ display: 'flex', justifyContent: 'flex-end', gap: 12 }}
              >
                <button
                  className="btn btn-ghost"
                  onClick={() => setRejectOpen(true)}
                  disabled={!canAct}
                >
                  Reddet
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleAccept}
                  disabled={!canAct}
                >
                  Kabul Et
                </button>
              </div>
            </div>
          </div>
        )}

        {errorMsg && (
          <p className="error-text" style={{ padding: '0 16px' }}>{errorMsg}</p>
        )}
      </div>

      {rejectOpen && (
        <RejectModal
          comment={rejectComment}
          onChange={setRejectComment}
          onCancel={() => {
            setRejectOpen(false)
            setRejectComment('')
          }}
          onSubmit={handleRejectSubmit}
          submitting={submitting}
        />
      )}
    </div>
  )
}

function EmptyQueue({ onRefresh }: { onRefresh: () => void }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 'calc(100vh - 160px)',
        gap: 12,
        textAlign: 'center',
        padding: 32,
      }}
    >
      <p style={{ fontSize: 'var(--fs-20)', color: 'var(--fg-2)', margin: 0 }}>
        Kuyrukta soru kalmadı.
      </p>
      <p style={{ color: 'var(--fg-3)', margin: 0, maxWidth: 520 }}>
        Yeni sorular üretmek için terminalden{' '}
        <code style={{ fontFamily: 'var(--font-mono)' }}>
          uv run python -m agents.cli generate-batch
        </code>{' '}
        komutunu çalıştır.
      </p>
      <button className="btn btn-primary" onClick={onRefresh}>
        Tazele
      </button>
    </div>
  )
}

interface RejectModalProps {
  comment: string
  onChange: (s: string) => void
  onCancel: () => void
  onSubmit: () => void
  submitting: boolean
}

function RejectModal({ comment, onChange, onCancel, onSubmit, submitting }: RejectModalProps) {
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(20, 14, 38, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={onCancel}
    >
      <div
        className="panel-card"
        style={{ width: 480, padding: 24, background: 'var(--bg-card)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontSize: 'var(--fs-20)', fontWeight: 600, marginBottom: 4 }}>
          Reddet
        </div>
        <p style={{ color: 'var(--fg-3)', margin: '0 0 12px' }}>
          Açıklama zorunlu. Bu kayıt, soru/cevap/oyun adımlarıyla birlikte sorun arşivine yazılacak.
        </p>
        <textarea
          className="input"
          rows={5}
          style={{ width: '100%', resize: 'vertical' }}
          placeholder="Neden reddediyorsun?"
          value={comment}
          onChange={(e) => onChange(e.target.value)}
          autoFocus
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
          <button className="btn btn-ghost" onClick={onCancel} disabled={submitting}>
            İptal
          </button>
          <button
            className="btn btn-primary"
            onClick={onSubmit}
            disabled={submitting || !comment.trim()}
          >
            {submitting ? 'Gönderiliyor…' : 'Gönder'}
          </button>
        </div>
      </div>
    </div>
  )
}
