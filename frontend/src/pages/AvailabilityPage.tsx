import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Availability, Professional } from '../types'
import '../patients.css'
import '../availability.css'

const weekdays = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
const timeOptions = Array.from({ length: 21 }, (_, index) => { const minutes = 8 * 60 + index * 30; return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}` })

export function AvailabilityPage() {
  const { user } = useAuth()
  const [professionals, setProfessionals] = useState<Professional[]>([])
  const [professionalId, setProfessionalId] = useState('')
  const [items, setItems] = useState<Availability[]>([])
  const [day, setDay] = useState(0)
  const [startTime, setStartTime] = useState('08:00')
  const [endTime, setEndTime] = useState('18:00')
  const [error, setError] = useState('')
  const effectiveId = user?.role === 'PROFISSIONAL' ? String(user.professional_id ?? '') : professionalId
  const load = async (id = effectiveId) => { if (!id) { setItems([]); return }; setItems(await api<Availability[]>(`/api/availability/${id}`)) }
  useEffect(() => { if (user?.role === 'ADMIN') api<Professional[]>('/api/professionals').then(setProfessionals).catch((item: Error) => setError(item.message)) }, [user?.role])
  useEffect(() => { void load().catch((item: Error) => setError(item.message)) }, [effectiveId])
  const selectedItems = useMemo(() => items.filter((item) => item.weekday === day), [items, day])
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!effectiveId) { setError('Selecione um profissional.'); return }
    if (startTime >= endTime) { setError('O fim do atendimento deve ser posterior ao início.'); return }
    setError('')
    try { await api(`/api/availability/${effectiveId}`, { method: 'POST', body: JSON.stringify({ weekday: day, start_time: startTime, end_time: endTime }) }); await load() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível salvar a disponibilidade.') }
  }
  const useDefaultDay = () => { setStartTime('08:00'); setEndTime('18:00') }
  const remove = async (id: number) => { if (!window.confirm('Remover este período de atendimento?')) return; try { await api(`/api/availability/${id}`, { method: 'DELETE' }); await load() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível remover o horário.') } }
  return <>
    <header className="page-heading"><div><h1>Disponibilidade</h1><p>Defina os períodos de atendimento por dia. A agenda só oferecerá horários dentro desses períodos.</p></div></header>
    {user?.role === 'ADMIN' && <label className="record-filter">Profissional<select value={professionalId} onChange={(event) => setProfessionalId(event.target.value)}><option value="">Selecione</option>{professionals.filter((professional) => professional.active).map((professional) => <option value={professional.id} key={professional.id}>{professional.name}</option>)}</select></label>}
    {effectiveId && <section className="availability-editor"><div className="day-picker">{weekdays.map((label, index) => <button type="button" className={day === index ? 'selected' : ''} onClick={() => setDay(index)} key={label}><strong>{label.slice(0, 3)}</strong><small>{items.filter((item) => item.weekday === index).length ? 'Configurado' : 'Sem horário'}</small></button>)}</div><div className="availability-day"><div><h2>{weekdays[day]}</h2><p>Escolha um período contínuo. Para pausa de almoço, adicione dois períodos separados.</p></div><button type="button" className="secondary-button" onClick={useDefaultDay}>Usar 08:00 — 18:00</button></div><form className="availability-form" onSubmit={submit}><label>Início<select value={startTime} onChange={(event) => setStartTime(event.target.value)}>{timeOptions.slice(0, -1).map((time) => <option value={time} key={time}>{time}</option>)}</select></label><label>Fim<select value={endTime} onChange={(event) => setEndTime(event.target.value)}>{timeOptions.slice(1).map((time) => <option value={time} key={time}>{time}</option>)}</select></label><button>Salvar período</button></form><section className="availability-list">{selectedItems.length ? selectedItems.map((item) => <article key={item.id}><strong>{item.start_time.slice(0, 5)} — {item.end_time.slice(0, 5)}</strong><span>Disponível para agendamentos</span><button className="danger-button" type="button" onClick={() => void remove(item.id)}>Remover</button></article>) : <p>Nenhum período configurado para este dia.</p>}</section></section>}
    {error && <p className="error">{error}</p>}
  </>
}
