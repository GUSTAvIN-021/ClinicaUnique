import { FormEvent, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { User } from '../types'

export function LoginPage() {
  const { user, refresh } = useAuth(); const navigate = useNavigate(); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); setBusy(true); setError(''); const values = new FormData(event.currentTarget); try { await api<User>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email: values.get('email'), password: values.get('password') }) }); await refresh(); navigate('/') } catch (e) { setError(e instanceof Error ? e.message : 'Falha ao entrar.') } finally { setBusy(false) } }
  return <main className="login"><form onSubmit={submit}><img className="login-logo" src="/unique-logo.jpg" alt="Unique Atendimento multidisciplinar" /><h1>Bem-vindo</h1><p>Acesse a gestão da sua clínica.</p><label>E-mail<input name="email" type="email" autoComplete="username" required /></label><label>Senha<input name="password" type="password" autoComplete="current-password" required minLength={8} /></label>{error && <p className="error">{error}</p>}<button disabled={busy}>{busy ? 'Entrando…' : 'Entrar'}</button></form></main>
}
