import { useState } from 'react'

interface Props {
  username: string
  onLogout: () => void
}

export default function UserAvatar({ username, onLogout }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="avatar-wrapper">
      <button
        className="avatar-btn"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      >
        {username[0]?.toUpperCase()}
      </button>
      {open && (
        <div className="avatar-dropdown">
          <button onClick={onLogout}>Sign out</button>
        </div>
      )}
    </div>
  )
}
