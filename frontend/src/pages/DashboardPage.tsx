import { useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Dashboard } from '../types'
import '../dashboard.css'

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null); const [error, setError] = useState('')
  useEffect(() => { api<Dashboard>('/api/dashboard').then(setData).catch((e: Error) => setError(e.message)) }, [])
  if (error) return <p className="error">{error}</p>
  if (!data) return <p>Carregando indicadores…</p>
  const overview = [['Pacientes', data.patients], ['Profissionais ativos', data.active_professionals], ['Atendimentos hoje', data.today_appointments], ['Atendimentos na semana', data.week_appointments]]
  const monthly = [['Atendimentos realizados', data.monthly_completed], ['Faltas', data.monthly_missed], ['Cancelamentos', data.monthly_cancelled], ['Novos pacientes', data.monthly_new_patients]]
  return <><header className="page-heading"><div><h1>Dashboard</h1><p>Visão geral da operação clínica.</p></div></header><section className="cards">{overview.map(([label, value]) => <article className="card" key={String(label)}><span>{label}</span><strong>{value}</strong></article>)}</section><h2 className="section-title">Indicadores do mês</h2><section className="cards">{monthly.map(([label, value]) => <article className="card" key={String(label)}><span>{label}</span><strong>{value}</strong></article>)}</section></>
}
