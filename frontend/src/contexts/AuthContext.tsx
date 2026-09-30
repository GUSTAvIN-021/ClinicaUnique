import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { User } from '../types'

type Auth = { user: User | null; loading: boolean; refresh: () => Promise<void>; logout: () => Promise<void> }
const AuthContext = createContext<Auth | null>(null)
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true)
  const refresh = async () => { try { const currentUser = await api<User>('/api/auth/me'); const csrf = await api<{ csrf_token: string }>('/api/auth/csrf'); document.cookie = `csrf_token=${encodeURIComponent(csrf.csrf_token)}; Path=/; SameSite=Lax`; setUser(currentUser) } catch { setUser(null) } finally { setLoading(false) } }
  const logout = async () => { await api<void>('/api/auth/logout', { method: 'POST' }); setUser(null) }
  useEffect(() => { void refresh() }, [])
  return <AuthContext.Provider value={{ user, loading, refresh, logout }}>{children}</AuthContext.Provider>
}
export const useAuth = () => { const context = useContext(AuthContext); if (!context) throw new Error('AuthProvider ausente'); return context }
