import UserAvatar from './UserAvatar'

type Lang = 'tr' | 'en'

interface Props {
  username: string
  onLogout: () => void
  lang: Lang
  onLangChange: (next: Lang) => void
  onPickMatematik: () => void
}

const TOPICS: { id: string; label: string; enabled: boolean }[] = [
  { id: 'matematik', label: 'Matematik', enabled: true },
  { id: 'turkce', label: 'Türkçe', enabled: false },
  { id: 'fen', label: 'Fen Bilimleri', enabled: false },
  { id: 'sosyal', label: 'Sosyal Bilgiler', enabled: false },
]

export default function TeacherTopicChooser({
  username,
  onLogout,
  lang,
  onLangChange,
  onPickMatematik,
}: Props) {
  return (
    <div className="app-shell" style={{ display: 'block', padding: 32 }}>
      <UserAvatar
        username={username}
        onLogout={onLogout}
        lang={lang}
        onLangChange={onLangChange}
      />

      <div style={{ maxWidth: 920, margin: '0 auto', paddingTop: 48 }}>
        <h1 style={{ fontSize: 'var(--fs-32)', margin: '0 0 8px' }}>Bir ders seçin</h1>
        <p style={{ color: 'var(--fg-3)', marginTop: 0, marginBottom: 32 }}>
          Şimdilik yalnızca Matematik aktif. Diğer dersler yakında.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 16,
          }}
        >
          {TOPICS.map((t) => (
            <button
              key={t.id}
              className="panel-card"
              onClick={t.enabled ? onPickMatematik : undefined}
              disabled={!t.enabled}
              style={{
                padding: 24,
                textAlign: 'left',
                cursor: t.enabled ? 'pointer' : 'not-allowed',
                opacity: t.enabled ? 1 : 0.5,
                border: t.enabled ? '2px solid var(--violet-500)' : '1px solid var(--ink-200)',
                background: 'var(--bg-card)',
              }}
              title={t.enabled ? '' : 'Yakında'}
            >
              <div style={{ fontSize: 'var(--fs-20)', fontWeight: 600 }}>{t.label}</div>
              <div
                style={{
                  fontSize: 12,
                  color: 'var(--fg-3)',
                  marginTop: 8,
                }}
              >
                {t.enabled ? 'Stüdyoya gir →' : 'Yakında'}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
