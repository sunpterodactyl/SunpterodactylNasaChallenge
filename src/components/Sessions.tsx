import { useState } from 'react'
import { useStore } from '../store'

export default function Sessions() {
  const sessions = useStore((s) => s.sessions)
  const saveSession = useStore((s) => s.saveSession)
  const openSession = useStore((s) => s.openSession)
  const renameSession = useStore((s) => s.renameSession)
  const deleteSession = useStore((s) => s.deleteSession)
  const exportSession = useStore((s) => s.exportSession)
  const [name, setName] = useState('')

  return (
    <div className="sessions">
      <span className="section-label">Saved sessions</span>
      <div className="session-save">
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Session name"
          aria-label="Session name"
        />
        <button
          type="button"
          onClick={() => {
            saveSession(name)
            setName('')
          }}
        >
          Save
        </button>
      </div>

      {sessions.length === 0 && (
        <p className="mock-note">No saved sessions yet. Star results, then save.</p>
      )}

      {sessions.map((s) => (
        <div key={s.id} className="session-row">
          <strong>{s.name}</strong>
          <time dateTime={s.createdAt}>
            {new Date(s.createdAt).toLocaleString()} · {s.starred.length} starred
          </time>
          <div className="session-actions">
            <button type="button" onClick={() => void openSession(s.id)}>
              Open
            </button>
            <button
              type="button"
              onClick={() => {
                const next = window.prompt('Rename session', s.name)
                if (next != null) renameSession(s.id, next)
              }}
            >
              Rename
            </button>
            <button type="button" onClick={() => exportSession(s.id)}>
              Export
            </button>
            <button
              type="button"
              onClick={() => {
                if (window.confirm(`Delete “${s.name}”?`)) deleteSession(s.id)
              }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}
