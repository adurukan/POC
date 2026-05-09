import { useEffect, useRef, useState } from 'react'

type Lang = 'tr' | 'en'

interface Props {
  username: string
  onLogout: () => void
  lang?: Lang
  onLangChange?: (lang: Lang) => void
}

const COPY: Record<Lang, { language: string; signOut: string }> = {
  tr: { language: 'Dil', signOut: 'Çıkış yap' },
  en: { language: 'Language', signOut: 'Sign out' },
}

/* ─── Inline icons (no extra deps) ─────────────────────────── */
function Icon({
  size = 16,
  children,
}: {
  size?: number
  children: React.ReactNode
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}
const IconLogout = () => (
  <Icon size={15}>
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
    <polyline points="16 17 21 12 16 7" />
    <line x1="21" y1="12" x2="9" y2="12" />
  </Icon>
)
const IconCheck = () => (
  <Icon size={15}>
    <polyline points="20 6 9 17 4 12" />
  </Icon>
)
const IconGlobe = () => (
  <Icon size={13}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18" />
    <path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18" />
  </Icon>
)

/* ─── Flag glyphs ──────────────────────────────────────────── */
function FlagTR() {
  return (
    <svg width={18} height={18} viewBox="0 0 24 24" aria-hidden="true">
      <rect width="24" height="24" rx="9" fill="#E30A17" />
      <circle cx="9.5" cy="12" r="4.4" fill="#fff" />
      <circle cx="10.6" cy="12" r="3.5" fill="#E30A17" />
      <path
        d="M14.4 12l-2.5.85.78-2.4-1.55-2.05 2.55.05.72-2.45.72 2.45 2.55-.05-1.55 2.05.78 2.4z"
        fill="#fff"
      />
    </svg>
  )
}
function FlagGB() {
  return (
    <svg width={18} height={18} viewBox="0 0 24 24" aria-hidden="true">
      <defs>
        <clipPath id="ua-gb-clip">
          <rect width="24" height="24" rx="9" />
        </clipPath>
      </defs>
      <g clipPath="url(#ua-gb-clip)">
        <rect width="24" height="24" fill="#012169" />
        <path d="M0 0L24 24M24 0L0 24" stroke="#fff" strokeWidth="3" />
        <path d="M12 0v24M0 12h24" stroke="#fff" strokeWidth="4" />
        <path d="M12 0v24M0 12h24" stroke="#C8102E" strokeWidth="2.2" />
      </g>
    </svg>
  )
}

export default function UserAvatar({
  username,
  onLogout,
  lang: controlledLang,
  onLangChange,
}: Props) {
  // Uncontrolled fallback: persist choice in localStorage
  const [internalLang, setInternalLang] = useState<Lang>(() => {
    const stored = localStorage.getItem('lang')
    return stored === 'en' ? 'en' : 'tr'
  })
  const lang = controlledLang ?? internalLang

  function setLang(next: Lang) {
    if (onLangChange) {
      onLangChange(next)
    } else {
      setInternalLang(next)
      localStorage.setItem('lang', next)
    }
  }

  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close on outside click + Escape
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [])

  const initial = username[0]?.toUpperCase() ?? '?'
  const c = COPY[lang]

  return (
    <div className="pb-wrap" ref={ref}>
      <button
        className={`pb-avatar ${open ? 'is-open' : ''}`}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={username}
      >
        {initial}
      </button>

      <div className={`pb-menu ${open ? 'is-open' : ''}`} role="menu">
        <div className="pb-menu__id">
          <div className="pb-menu__avatar-lg">{initial}</div>
          <div className="pb-menu__id-text">
            <div className="pb-menu__name">{username}</div>
          </div>
        </div>

        <div className="pb-menu__section">
          <div className="pb-menu__label">
            <IconGlobe /> {c.language}
          </div>
          <button
            className={`pb-row ${lang === 'tr' ? 'is-active' : ''}`}
            onClick={() => setLang('tr')}
            role="menuitemradio"
            aria-checked={lang === 'tr'}
          >
            <FlagTR />
            <span className="pb-row__label">Türkçe</span>
            {lang === 'tr' && (
              <span style={{ color: 'var(--violet-600)' }}>
                <IconCheck />
              </span>
            )}
          </button>
          <button
            className={`pb-row ${lang === 'en' ? 'is-active' : ''}`}
            onClick={() => setLang('en')}
            role="menuitemradio"
            aria-checked={lang === 'en'}
          >
            <FlagGB />
            <span className="pb-row__label">English</span>
            {lang === 'en' && (
              <span style={{ color: 'var(--violet-600)' }}>
                <IconCheck />
              </span>
            )}
          </button>
        </div>

        <div className="pb-menu__divider" />

        <button
          className="pb-menu__action pb-menu__action--danger"
          onClick={onLogout}
        >
          <IconLogout />
          <span>{c.signOut}</span>
        </button>
      </div>
    </div>
  )
}
