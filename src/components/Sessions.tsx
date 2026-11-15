import { useState } from 'react'
import type { Session } from '../types'

interface Props {
  sessions: Session[]
  notes: string
  starredCount: number
  onNotes: (s: string) => void
  onSave: (name: string) => void
  onLoad: (s: Session) => void
  onDelete: (name: string) => void
}

export default function Sessions({ sessions, notes, starredCount, onNotes, onSave, onLoad, onDelete }: Props) {
  const [name, setName] = useState('')
  return (
    <section className="sessions" aria-labelledby="sessions-h">
      <h2 id="sessions-h">Sessions</h2>
      <label className="field">
        <span>Notes</span>
        <textarea rows={2} value={notes} onChange={(e) => onNotes(e.target.value)} placeholder="What are you testing?" />
      </label>
      <form
        className="save-row"
        onSubmit={(e) => {
          e.preventDefault()
          if (!name.trim()) return
          onSave(name.trim())
          setName('')
        }}
      >
        <input aria-label="Session name" placeholder="Session name" value={name} onChange={(e) => setName(e.target.value)} />
        <button type="submit" disabled={!name.trim()}>
          Save
        </button>
      </form>
      <small className="hint">Saves the brief, {starredCount} starred patch{starredCount === 1 ? '' : 'es'} and notes in this browser.</small>
      {sessions.length === 0 ? (
        <p className="empty-note">No saved sessions yet.</p>
      ) : (
        <ul className="session-list">
          {sessions.map((s) => (
            <li key={s.name}>
              <button className="link" onClick={() => onLoad(s)} title={s.notes || undefined}>
                <b>{s.name}</b>
                <span>
                  {s.brief.target_id} · {s.brief.objective} · {s.starred.length}★
                </span>
              </button>
              <button className="icon" aria-label={`Delete session ${s.name}`} onClick={() => onDelete(s.name)}>
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
