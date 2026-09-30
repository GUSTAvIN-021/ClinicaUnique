import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Availability, Professional } from '../types'
import '../patients.css'
import '../availability.css'

const weekdays = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

export function AvailabilityPage() {
  const { user } = useAuth(); const [professionals, setProfessionals] = useState<Professional[]>([]); const [professionalId, setProfessionalId] = useState(''); const [items, setItems] = useState<Availability[]>([]); const [day, setDay] = useState(0); const [error, setError] = useState('')
  const effectiveId = user?.role === 'PROFISSIONAL' ? String(user.professional_id ?? '') : professionalId
  const load = (id: string) => { if (!id) { setItems([]); return } api<Availability[]>(`/api/availability/${id}`).then(setItems).catch((e: Error) => setError(e.message)) }
  useEffect(() => { if (user?.role === 'ADMIN') api<Professional[]>('/api/professionals').then(setProfessionals).catch((e: Error) => setError(e.message)) }, [user?.role])
  useEffect(() => { load(effectiveId) }, [effectiveId])
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); if (!effectiveId) { setError('Selecione um profissional.'); return } const formElement = event.currentTarget; const form = new FormData(formElement); setError(''); try { await api(`/api/availability/${effectiveId}`, { method: 'POST', body: JSON.stringify({ weekday: day, start_time: form.get('start_time'), end_time: form.get('end_time') }) }); formElement.reset(); await load(effectiveId) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível salvar a disponibilidade.') } }
  const remove = async (id: number) => { if (!window.confirm('Remover este horário de disponibilidade?')) return; try { await api(`/api/availability/${id}`, { method: 'DELETE' }); await load(effectiveId) } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível remover o horário.') } }
  const selectedItems = items.filter((item) => item.weekday === day)
  return <><header className="page-heading"><div><h1>Disponibilidade</h1><p>Selecione um dia e adicione os intervalos de atendimento desse dia.</p></div></header>{user?.role === 'ADMIN' && <label className="record-filter">Profissional<select value={professionalId} onChange={(event) => setProfessionalId(event.target.value)}><option value="">Selecione</option>{professionals.map((professional) => <option value={professional.id} key={professional.id}>{professional.name}</option>)}</select></label>}{effectiveId && <><div className="day-picker">{weekdays.map((label, index) => <button className={day === index ? 'selected' : ''} onClick={() => setDay(index)} key={label}>{label.slice(0, 3)}</button>)}</div><h2 className="selected-day">{weekdays[day]}</h2><form className="entry-form" onSubmit={submit}><input name="start_time" type="time" aria-label="Início" required /><input name="end_time" type="time" aria-label="Fim" required /><button>Adicionar horário</button></form><section className="availability-list">{selectedItems.length ? selectedItems.map((item) => <article key={item.id}><strong>{item.start_time.slice(0, 5)} — {item.end_time.slice(0, 5)}</strong><button className="danger-button" onClick={() => void remove(item.id)}>Remover</button></article>) : <p>Nenhum horário configurado para este dia.</p>}</section></>}{error && <p className="error">{error}</p>}</> }
