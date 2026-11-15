import type { Session } from './types'

const KEY = 'terrain.sessions'

export function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function storeSessions(sessions: Session[]): boolean {
  try {
    localStorage.setItem(KEY, JSON.stringify(sessions))
    return true
  } catch {
    return false
  }
}
