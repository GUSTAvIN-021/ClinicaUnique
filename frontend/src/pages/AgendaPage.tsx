import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Appointment, Availability, Patient, Professional } from '../types'
import '../patients.css'
import '../agenda.css'

const pad = (value: number) => String(value).padStart(2, '0')
const toIsoDate = (value: Date) => `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
const dateFromIso = (value: string) => new Date(`${value}T12:00:00`)
const mondayOf = (value: Date) => { const copy = new Date(value); copy.setDate(copy.getDate() - ((copy.getDay() + 6) % 7)); return copy }
const addDays = (value: Date, days: number) => { const copy = new Date(value); copy.setDate(copy.getDate() + days); return copy }
const formatDate = (value: string) => dateFromIso(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })
const minutes = (value: string) => { const [hour, minute] = value.slice(0, 5).split(':').map(Number); return hour * 60 + minute }
const asTime = (value: number) => `${pad(Math.floor(value / 60))}:${pad(value % 60)}`
const weekdays = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

export function AgendaPage() {
  const { user } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [professionals, setProfessionals] = useState<Professional[]>([])
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [availability, setAvailability] = useState<Availability[]>([])
  const [referenceDate, setReferenceDate] = useState(toIsoDate(new Date()))
  const [filterProfessionalId, setFilterProfessionalId] = useState('')
  const [search, setSearch] = useState('')
  const [formProfessionalId, setFormProfessionalId] = useState('')
  const [formDate, setFormDate] = useState(toIsoDate(new Date()))
  const [duration, setDuration] = useState(30)
  const [startTime, setStartTime] = useState('')
  const [recurrenceWeeks, setRecurrenceWeeks] = useState(0)
  const [editing, setEditing] = useState<Appointment | null>(null)
  const [editProfessionalId, setEditProfessionalId] = useState('')
  const [editDate, setEditDate] = useState('')
  const [editDuration, setEditDuration] = useState(30)
  const [editStartTime, setEditStartTime] = useState('')
  const [editAvailability, setEditAvailability] = useState<Availability[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const effectiveFilter = user?.role === 'PROFISSIONAL' ? String(user.professional_id ?? '') : filterProfessionalId
  const weekStart = useMemo(() => mondayOf(dateFromIso(referenceDate)), [referenceDate])
  const days = useMemo(() => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)), [weekStart])
  const selectedProfessionalId = user?.role === 'PROFISSIONAL' ? String(user.professional_id ?? '') : formProfessionalId

  const loadAppointments = async () => {
    const params = new URLSearchParams({ date_from: toIsoDate(weekStart), date_to: toIsoDate(addDays(weekStart, 6)) })
    if (effectiveFilter) params.set('professional_id', effectiveFilter)
    setAppointments(await api<Appointment[]>(`/api/appointments?${params.toString()}`))
  }
  const loadAvailability = (professionalId: string, setItems: (items: Availability[]) => void) => {
    if (!professionalId) { setItems([]); return }
    api<Availability[]>(`/api/availability/${professionalId}`).then(setItems).catch((item: Error) => setError(item.message))
  }

  useEffect(() => {
    api<Patient[]>('/api/patients').then(setPatients).catch((item: Error) => setError(item.message))
    api<Professional[]>('/api/professionals').then(setProfessionals).catch((item: Error) => setError(item.message))
  }, [])
  useEffect(() => { void loadAppointments().catch((item: Error) => setError(item.message)) }, [referenceDate, effectiveFilter])
  useEffect(() => { setStartTime(''); loadAvailability(selectedProfessionalId, setAvailability) }, [selectedProfessionalId])
  useEffect(() => { if (editing) loadAvailability(editProfessionalId, setEditAvailability) }, [editing, editProfessionalId])

  const slotsFor = (professionalId: string, appointmentDate: string, selectedDuration: number, items: Availability[], ignoredId?: number) => {
    if (!professionalId || !appointmentDate) return []
    const weekday = (dateFromIso(appointmentDate).getDay() + 6) % 7
    const output = new Set<string>()
    items.filter((item) => item.weekday === weekday).forEach((item) => {
      for (let current = minutes(item.start_time); current + selectedDuration <= minutes(item.end_time); current += 30) {
        const endsAt = current + selectedDuration
        const conflicts = appointments.some((appointment) => appointment.id !== ignoredId && appointment.status !== 'CANCELADO' && appointment.professional_id === Number(professionalId) && appointment.appointment_date === appointmentDate && minutes(appointment.start_time) < endsAt && minutes(appointment.end_time) > current)
        if (!conflicts) output.add(asTime(current))
      }
    })
    return [...output].sort()
  }
  const slots = useMemo(() => slotsFor(selectedProfessionalId, formDate, duration, availability), [selectedProfessionalId, formDate, duration, availability, appointments])
  const editSlots = useMemo(() => slotsFor(editProfessionalId, editDate, editDuration, editAvailability, editing?.id), [editProfessionalId, editDate, editDuration, editAvailability, editing, appointments])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement)
    if (!selectedProfessionalId || !startTime) { setError('Selecione o profissional, a data e um horário disponível.'); return }
    setSaving(true); setError('')
    try { const payload = { patient_id: Number(form.get('patient_id')), professional_id: Number(selectedProfessionalId), appointment_date: formDate, start_time: startTime, end_time: asTime(minutes(startTime) + duration), notes: form.get('notes') || null, ...(recurrenceWeeks ? { weeks: recurrenceWeeks } : {}) }; await api(recurrenceWeeks ? '/api/appointments/recurring' : '/api/appointments', { method: 'POST', body: JSON.stringify(payload) }); formElement.reset(); setStartTime(''); setRecurrenceWeeks(0); await loadAppointments() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível criar o agendamento.') } finally { setSaving(false) }
  }
  const beginEdit = (appointment: Appointment) => {
    setEditing(appointment); setEditProfessionalId(String(appointment.professional_id)); setEditDate(appointment.appointment_date); setEditStartTime(appointment.start_time.slice(0, 5)); setEditDuration(minutes(appointment.end_time) - minutes(appointment.start_time)); setError('')
  }
  const saveEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!editing || !editProfessionalId || !editStartTime) { setError('Preencha os dados do agendamento.'); return }
    const form = new FormData(event.currentTarget); setSaving(true); setError('')
    try { await api(`/api/appointments/${editing.id}`, { method: 'PATCH', body: JSON.stringify({ patient_id: Number(form.get('patient_id')), professional_id: Number(editProfessionalId), appointment_date: editDate, start_time: editStartTime, end_time: asTime(minutes(editStartTime) + editDuration), notes: form.get('notes') || null }) }); setEditing(null); await loadAppointments() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível editar o agendamento.') } finally { setSaving(false) }
  }
  const changeStatus = async (id: number, status: string) => { try { await api(`/api/appointments/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }); await loadAppointments() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível atualizar o status.') } }
  const cancel = async (appointment: Appointment) => { if (!window.confirm(`Cancelar o atendimento de ${patientName(appointment.patient_id)}?`)) return; await changeStatus(appointment.id, 'CANCELADO') }
  const cancelSeries = async (appointment: Appointment) => { if (!window.confirm(`Cancelar toda a série de atendimentos de ${patientName(appointment.patient_id)}?`)) return; try { await api(`/api/appointments/${appointment.id}/series`, { method: 'DELETE' }); await loadAppointments() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível cancelar a série.') } }
  const patientName = (id: number) => patients.find((item) => item.id === id)?.name ?? `Paciente #${id}`
  const professionalName = (id: number) => professionals.find((item) => item.id === id)?.name ?? `Profissional #${id}`
  const searchedAppointments = appointments.filter((item) => `${patientName(item.patient_id)} ${professionalName(item.professional_id)}`.toLocaleLowerCase('pt-BR').includes(search.trim().toLocaleLowerCase('pt-BR')))

  return <>
    <header className="page-heading agenda-top"><div><h1>Agenda</h1><p>Gerencie os atendimentos por profissional e por semana.</p></div><div className="agenda-top-actions"><button type="button" className="secondary-button" onClick={() => window.print()}>Imprimir agenda</button></div></header>
    <section className="schedule-card"><h2>Novo agendamento</h2><form onSubmit={submit}><div className="schedule-grid">
      <label className="field">Paciente<select name="patient_id" required defaultValue=""><option value="" disabled>Selecione um paciente</option>{patients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      {user?.role === 'ADMIN' ? <label className="field">Profissional<select required value={formProfessionalId} onChange={(event) => setFormProfessionalId(event.target.value)}><option value="" disabled>Selecione um profissional</option>{professionals.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : <label className="field">Profissional<input value={professionalName(Number(selectedProfessionalId))} disabled /></label>}
      <label className="field">Data<input type="date" required value={formDate} onChange={(event) => setFormDate(event.target.value)} /></label><label className="field">Duração<select value={duration} onChange={(event) => setDuration(Number(event.target.value))}><option value={30}>30 minutos</option><option value={60}>1 hora</option><option value={90}>1 hora e 30 minutos</option><option value={120}>2 horas</option></select></label>
      <label className="field">Horário inicial<select required value={startTime} onChange={(event) => setStartTime(event.target.value)} disabled={!slots.length}><option value="">{selectedProfessionalId ? 'Selecione um horário' : 'Selecione um profissional'}</option>{slots.map((item) => <option value={item} key={item}>{item}</option>)}</select>{selectedProfessionalId && !slots.length && <small>Não há horário livre nessa data.</small>}</label><label className="field">Observações<input name="notes" placeholder="Opcional" /></label>
      <label className="field recurrence-field"><span><input type="checkbox" checked={recurrenceWeeks > 0} onChange={(event) => setRecurrenceWeeks(event.target.checked ? 4 : 0)} /> Repetir semanalmente</span>{recurrenceWeeks > 0 && <select value={recurrenceWeeks} onChange={(event) => setRecurrenceWeeks(Number(event.target.value))}><option value={4}>4 semanas</option><option value={8}>8 semanas</option><option value={12}>12 semanas</option><option value={16}>16 semanas</option><option value={24}>24 semanas</option></select>}</label>
    </div><div className="schedule-actions"><button disabled={saving}>{saving ? 'Agendando…' : 'Agendar'}</button></div></form></section>
    {editing && <section className="schedule-card edit-appointment"><h2>Editar agendamento</h2><form onSubmit={saveEdit}><div className="schedule-grid"><label className="field">Paciente<select name="patient_id" defaultValue={editing.patient_id} required>{patients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{user?.role === 'ADMIN' ? <label className="field">Profissional<select value={editProfessionalId} onChange={(event) => { setEditProfessionalId(event.target.value); setEditStartTime('') }} required>{professionals.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : <label className="field">Profissional<input value={professionalName(Number(editProfessionalId))} disabled /></label>}<label className="field">Data<input type="date" value={editDate} onChange={(event) => { setEditDate(event.target.value); setEditStartTime('') }} required /></label><label className="field">Duração<select value={editDuration} onChange={(event) => { setEditDuration(Number(event.target.value)); setEditStartTime('') }}><option value={30}>30 minutos</option><option value={60}>1 hora</option><option value={90}>1 hora e 30 minutos</option><option value={120}>2 horas</option></select></label><label className="field">Horário inicial<select value={editStartTime} onChange={(event) => setEditStartTime(event.target.value)} required><option value="">Selecione um horário</option>{editSlots.map((item) => <option value={item} key={item}>{item}</option>)}</select></label><label className="field">Observações<input name="notes" defaultValue={editing.notes ?? ''} /></label></div><div className="schedule-actions"><button disabled={saving}>{saving ? 'Salvando…' : 'Salvar alterações'}</button><button type="button" className="secondary-button" onClick={() => setEditing(null)}>Cancelar edição</button></div></form></section>}
    <section className="agenda-panel"><div className="view-controls"><label className="field">Semana de<input type="date" value={referenceDate} onChange={(event) => setReferenceDate(event.target.value)} /></label>{user?.role === 'ADMIN' && <label className="field">Profissional<select value={filterProfessionalId} onChange={(event) => setFilterProfessionalId(event.target.value)}><option value="">Todos os profissionais</option>{professionals.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label className="field search-field">Buscar<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Paciente ou profissional" /></label><button type="button" onClick={() => setReferenceDate(toIsoDate(addDays(weekStart, -7)))}>Semana anterior</button><button type="button" onClick={() => setReferenceDate(toIsoDate(new Date()))}>Hoje</button><button type="button" onClick={() => setReferenceDate(toIsoDate(addDays(weekStart, 7)))}>Próxima semana</button></div>
      <h2>Atendimentos — {formatDate(toIsoDate(weekStart))} a {formatDate(toIsoDate(addDays(weekStart, 6)))}</h2><div className="week-grid">{days.map((day, index) => { const iso = toIsoDate(day); const appointmentsOfDay = searchedAppointments.filter((item) => item.appointment_date === iso); return <section className="week-day" key={iso}><h3>{weekdays[index]}<small>{formatDate(iso)}</small></h3>{appointmentsOfDay.length ? appointmentsOfDay.map((item) => <article className={`appointment ${item.status.toLowerCase()}`} key={item.id}><div className="appointment-time">{item.start_time.slice(0, 5)}</div><div className="appointment-info"><strong>{patientName(item.patient_id)}</strong><small>{professionalName(item.professional_id)} · até {item.end_time.slice(0, 5)}</small><span className="appointment-status">{item.status}{item.recurrence_group_id ? ' · Recorrente' : ''}</span></div><div className="appointment-actions"><button type="button" className="secondary-button" onClick={() => beginEdit(item)}>Editar</button>{item.status === 'AGENDADO' && <button type="button" onClick={() => void changeStatus(item.id, 'CONFIRMADO')}>Confirmar</button>}{!['REALIZADO', 'FALTOU', 'CANCELADO'].includes(item.status) && <><button type="button" onClick={() => void changeStatus(item.id, 'REALIZADO')}>Realizado</button><button type="button" onClick={() => void changeStatus(item.id, 'FALTOU')}>Faltou</button><button type="button" className="danger-button" onClick={() => void cancel(item)}>Cancelar</button>{item.recurrence_group_id && <button type="button" className="danger-button" onClick={() => void cancelSeries(item)}>Cancelar série</button>}</>}</div></article>) : <p className="empty-day">Sem atendimentos.</p>}</section> })}</div>
    </section>{error && <p className="error">{error}</p>}
  </>
}
