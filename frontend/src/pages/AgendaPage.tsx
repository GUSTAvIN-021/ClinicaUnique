import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
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
const releasesSlot = (status: string) => ['CANCELADO', 'FALTOU', 'FALTOU_PROFISSIONAL'].includes(status)
const mayReceiveOutcome = (status: string) => !['REALIZADO', 'FALTOU', 'FALTOU_PROFISSIONAL', 'CANCELADO'].includes(status)
const statusLabel = (status: string) => ({
  AGENDADO: 'Pendente',
  CONFIRMADO: 'Confirmado',
  REALIZADO: 'Concluído',
  FALTOU: 'Paciente faltou',
  FALTOU_PROFISSIONAL: 'Profissional faltou',
  CANCELADO: 'Cancelado',
}[status] ?? status)
const appointmentServices = [
  { id: 'DURACAO_30', label: '30 minutos (1 horário)', duration: 30 },
  { id: 'DURACAO_60', label: '1 hora (2 horários)', duration: 60 },
  { id: 'DURACAO_90', label: '1 hora e 30 minutos (3 horários)', duration: 90 },
  { id: 'DURACAO_120', label: '2 horas (4 horários)', duration: 120 },
]

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
  const [serviceType, setServiceType] = useState(appointmentServices[0].id)
  const [duration, setDuration] = useState(appointmentServices[0].duration)
  const [startTime, setStartTime] = useState('')
  const [isRecurring, setIsRecurring] = useState(false)
  const [editing, setEditing] = useState<Appointment | null>(null)
  const editSectionRef = useRef<HTMLElement | null>(null)
  const [therapistActionAppointment, setTherapistActionAppointment] = useState<Appointment | null>(null)
  const [editProfessionalId, setEditProfessionalId] = useState('')
  const [editDate, setEditDate] = useState('')
  const [editServiceType, setEditServiceType] = useState(appointmentServices[0].id)
  const [editDuration, setEditDuration] = useState(appointmentServices[0].duration)
  const [editStartTime, setEditStartTime] = useState('')
  const [editAvailability, setEditAvailability] = useState<Availability[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [agendaView, setAgendaView] = useState<'week' | 'therapists'>('week')
  const [selectedDayIndex, setSelectedDayIndex] = useState(0)

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
  useEffect(() => { if (editing) editSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }, [editing])

  const slotsFor = (professionalId: string, appointmentDate: string, selectedDuration: number, items: Availability[], ignoredId?: number) => {
    if (!professionalId || !appointmentDate) return []
    const weekday = (dateFromIso(appointmentDate).getDay() + 6) % 7
    const output = new Set<string>()
    items.filter((item) => item.weekday === weekday).forEach((item) => {
      for (let current = minutes(item.start_time); current + selectedDuration <= minutes(item.end_time); current += 30) {
        const endsAt = current + selectedDuration
        const conflicts = appointments.some((appointment) => appointment.id !== ignoredId && !releasesSlot(appointment.status) && appointment.professional_id === Number(professionalId) && appointment.appointment_date === appointmentDate && minutes(appointment.start_time) < endsAt && minutes(appointment.end_time) > current)
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
    try { const service = appointmentServices.find((item) => item.id === serviceType)!; const payload = { patient_id: Number(form.get('patient_id')), professional_id: Number(selectedProfessionalId), appointment_date: formDate, start_time: startTime, end_time: asTime(minutes(startTime) + duration), service_type: service.id, notes: form.get('notes') || null }; await api(isRecurring ? '/api/appointments/recurring' : '/api/appointments', { method: 'POST', body: JSON.stringify(payload) }); formElement.reset(); setStartTime(''); setIsRecurring(false); await loadAppointments() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível criar o agendamento.') } finally { setSaving(false) }
  }
  const beginEdit = (appointment: Appointment) => {
    const currentDuration = minutes(appointment.end_time) - minutes(appointment.start_time)
    const service = appointmentServices.find((item) => item.id === appointment.service_type) ?? appointmentServices.find((item) => item.duration === currentDuration) ?? appointmentServices[0]
    setEditing(appointment); setEditProfessionalId(String(appointment.professional_id)); setEditDate(appointment.appointment_date); setEditStartTime(appointment.start_time.slice(0, 5)); setEditServiceType(service.id); setEditDuration(service.duration); setError('')
  }
  const saveEdit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!editing || !editProfessionalId || !editStartTime) { setError('Preencha os dados do agendamento.'); return }
    const form = new FormData(event.currentTarget); setSaving(true); setError('')
    try { const service = appointmentServices.find((item) => item.id === editServiceType)!; await api(`/api/appointments/${editing.id}`, { method: 'PATCH', body: JSON.stringify({ patient_id: Number(form.get('patient_id')), professional_id: Number(editProfessionalId), appointment_date: editDate, start_time: editStartTime, end_time: asTime(minutes(editStartTime) + editDuration), service_type: service.id, notes: form.get('notes') || null }) }); setEditing(null); await loadAppointments() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível editar o agendamento.') } finally { setSaving(false) }
  }
  const changeStatus = async (id: number, status: string) => { try { await api(`/api/appointments/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }) }); await loadAppointments() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível atualizar o status.') } }
  const cancel = async (appointment: Appointment) => { if (!window.confirm(`Cancelar o atendimento de ${patientName(appointment.patient_id)}?`)) return; await changeStatus(appointment.id, 'CANCELADO') }
  const removeCancelled = async (appointment: Appointment) => { if (!window.confirm(`Excluir definitivamente o atendimento cancelado de ${patientName(appointment.patient_id)}?`)) return; try { await api(`/api/appointments/${appointment.id}`, { method: 'DELETE' }); await loadAppointments() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível excluir o agendamento.') } }
  const cancelSeries = async (appointment: Appointment) => { if (!window.confirm(`Encerrar a recorrência de ${patientName(appointment.patient_id)}? Os atendimentos futuros já criados serão cancelados; o histórico será preservado.`)) return; try { await api(`/api/appointments/${appointment.id}/series`, { method: 'DELETE' }); await loadAppointments() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível encerrar a recorrência.') } }
  const patientName = (id: number) => patients.find((item) => item.id === id)?.name ?? `Paciente #${id}`
  const professionalName = (id: number) => professionals.find((item) => item.id === id)?.name ?? `Profissional #${id}`
  const searchedAppointments = appointments.filter((item) => `${patientName(item.patient_id)} ${professionalName(item.professional_id)}`.toLocaleLowerCase('pt-BR').includes(search.trim().toLocaleLowerCase('pt-BR')))

  return <>
    <header className="page-heading agenda-top"><div><h1>Agenda</h1><p>Gerencie os atendimentos por profissional e por semana.</p></div><div className="agenda-top-actions"><button type="button" className="secondary-button" onClick={() => window.print()}>Imprimir agenda</button></div></header>
    <section className="schedule-card"><h2>Novo agendamento</h2><form onSubmit={submit}><div className="schedule-grid">
      <label className="field">Paciente<select name="patient_id" required defaultValue=""><option value="" disabled>Selecione um paciente</option>{patients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      {user?.role === 'ADMIN' ? <label className="field">Profissional<select required value={formProfessionalId} onChange={(event) => setFormProfessionalId(event.target.value)}><option value="" disabled>Selecione um profissional</option>{professionals.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : <label className="field">Profissional<input value={professionalName(Number(selectedProfessionalId))} disabled /></label>}
      <label className="field">Data<input type="date" required value={formDate} onChange={(event) => setFormDate(event.target.value)} /></label><label className="field">Duração<select value={serviceType} onChange={(event) => { const service = appointmentServices.find((item) => item.id === event.target.value)!; setServiceType(service.id); setDuration(service.duration); setStartTime('') }}>{appointmentServices.map((service) => <option key={service.id} value={service.id}>{service.label}</option>)}</select></label>
      <label className="field">Horário inicial<select required value={startTime} onChange={(event) => setStartTime(event.target.value)} disabled={!slots.length}><option value="">{selectedProfessionalId ? 'Selecione um horário' : 'Selecione um profissional'}</option>{slots.map((item) => <option value={item} key={item}>{item}</option>)}</select>{selectedProfessionalId && !slots.length && <small>Não há horário livre nessa data.</small>}{slots.length > 0 && <small>Último início disponível: {slots[slots.length - 1]} — termina às {asTime(minutes(slots[slots.length - 1]) + duration)}.</small>}</label><label className="field">Observações<input name="notes" placeholder="Opcional" /></label>
      <label className="field recurrence-field"><span><input type="checkbox" checked={isRecurring} onChange={(event) => setIsRecurring(event.target.checked)} /> Repetir semanalmente sem data final</span>{isRecurring && <small>A série continuará ativa até usar “Encerrar recorrência”. A agenda cria somente as semanas visualizadas.</small>}</label>
    </div><div className="schedule-actions"><button disabled={saving}>{saving ? 'Agendando…' : 'Agendar'}</button></div></form></section>
    {editing && <section ref={editSectionRef} className="schedule-card edit-appointment"><h2>Editar agendamento</h2><form onSubmit={saveEdit}><div className="schedule-grid"><label className="field">Paciente<select name="patient_id" defaultValue={editing.patient_id} required>{patients.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{user?.role === 'ADMIN' ? <label className="field">Profissional<select value={editProfessionalId} onChange={(event) => { setEditProfessionalId(event.target.value); setEditStartTime('') }} required>{professionals.filter((item) => item.active).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : <label className="field">Profissional<input value={professionalName(Number(editProfessionalId))} disabled /></label>}<label className="field">Data<input type="date" value={editDate} onChange={(event) => { setEditDate(event.target.value); setEditStartTime('') }} required /></label><label className="field">Duração<select value={editServiceType} onChange={(event) => { const service = appointmentServices.find((item) => item.id === event.target.value)!; setEditServiceType(service.id); setEditDuration(service.duration); setEditStartTime('') }}>{appointmentServices.map((service) => <option key={service.id} value={service.id}>{service.label}</option>)}</select></label><label className="field">Horário inicial<select value={editStartTime} onChange={(event) => setEditStartTime(event.target.value)} required><option value="">Selecione um horário</option>{editSlots.map((item) => <option value={item} key={item}>{item}</option>)}</select></label><label className="field">Observações<input name="notes" defaultValue={editing.notes ?? ''} /></label></div><div className="schedule-actions"><button disabled={saving}>{saving ? 'Salvando…' : 'Salvar alterações'}</button><button type="button" className="secondary-button" onClick={() => setEditing(null)}>Cancelar edição</button></div></form></section>}
    <section className={`agenda-panel ${agendaView === 'therapists' ? 'therapist-mode' : ''}`}><div className="view-controls"><label className="field">Semana de<input type="date" value={referenceDate} onChange={(event) => setReferenceDate(event.target.value)} /></label>{user?.role === 'ADMIN' && <label className="field">Profissional<select value={filterProfessionalId} onChange={(event) => setFilterProfessionalId(event.target.value)}><option value="">Todos os profissionais</option>{professionals.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label className="field search-field">Buscar<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Paciente ou profissional" /></label><button type="button" onClick={() => setReferenceDate(toIsoDate(addDays(weekStart, -7)))}>Semana anterior</button><button type="button" onClick={() => setReferenceDate(toIsoDate(new Date()))}>Hoje</button><button type="button" onClick={() => setReferenceDate(toIsoDate(addDays(weekStart, 7)))}>Próxima semana</button><div className="agenda-view-switch"><button type="button" className={agendaView === 'week' ? 'selected' : ''} onClick={() => setAgendaView('week')}>Semana</button><button type="button" className={agendaView === 'therapists' ? 'selected' : ''} onClick={() => setAgendaView('therapists')}>Por terapeuta</button></div></div>
      <h2>Atendimentos — {formatDate(toIsoDate(weekStart))} a {formatDate(toIsoDate(addDays(weekStart, 6)))}</h2>
      <div className="agenda-legend" aria-label="Legenda dos status"><span className="agendado">Pendente</span><span className="confirmado">Confirmado</span><span className="realizado">Concluído</span><span className="faltou">Faltou / horário liberado</span></div>
      <div className="week-grid">{days.map((day, index) => { const iso = toIsoDate(day); const appointmentsOfDay = searchedAppointments.filter((item) => item.appointment_date === iso); return <section className="week-day" key={iso}><h3>{weekdays[index]}<small>{formatDate(iso)}</small></h3>{appointmentsOfDay.length ? appointmentsOfDay.map((item) => <article className={`appointment ${item.status.toLowerCase()}`} key={item.id}><div className="appointment-time">{item.start_time.slice(0, 5)}</div><div className="appointment-info"><strong>{patientName(item.patient_id)}</strong><small>{professionalName(item.professional_id)} · até {item.end_time.slice(0, 5)}</small><span className="appointment-status">{statusLabel(item.status)}{item.recurrence_group_id ? ' · Recorrente' : ''}</span></div><AppointmentActions appointment={item} onOpen={beginEdit} onStatus={changeStatus} onCancel={cancel} onCancelSeries={cancelSeries} onDelete={removeCancelled} /></article>) : <p className="empty-day">Sem atendimentos.</p>}</section> })}</div>
      <TherapistBoard days={days} selectedDayIndex={selectedDayIndex} onSelectDay={setSelectedDayIndex} appointments={searchedAppointments} professionals={professionals} filterProfessionalId={effectiveFilter} patientName={patientName} onOpenActions={setTherapistActionAppointment} />
      {therapistActionAppointment && <section className="therapist-action-panel"><div><strong>{patientName(therapistActionAppointment.patient_id)}</strong><span>{therapistActionAppointment.start_time.slice(0, 5)}–{therapistActionAppointment.end_time.slice(0, 5)} · {statusLabel(therapistActionAppointment.status)}</span><button type="button" className="secondary-button" onClick={() => setTherapistActionAppointment(null)}>Fechar</button></div><AppointmentActions appointment={therapistActionAppointment} onOpen={(appointment) => { setTherapistActionAppointment(null); beginEdit(appointment) }} onStatus={async (id, status) => { await changeStatus(id, status); setTherapistActionAppointment(null) }} onCancel={async (appointment) => { await cancel(appointment); setTherapistActionAppointment(null) }} onCancelSeries={async (appointment) => { await cancelSeries(appointment); setTherapistActionAppointment(null) }} onDelete={async (appointment) => { await removeCancelled(appointment); setTherapistActionAppointment(null) }} /></section>}
    </section>{error && <p className="error">{error}</p>}
  </>
}

type AppointmentActionProps = { appointment: Appointment; onOpen: (appointment: Appointment) => void; onStatus: (id: number, status: string) => Promise<void>; onCancel: (appointment: Appointment) => Promise<void>; onCancelSeries: (appointment: Appointment) => Promise<void>; onDelete: (appointment: Appointment) => Promise<void> }

function AppointmentActions({ appointment, onOpen, onStatus, onCancel, onCancelSeries, onDelete }: AppointmentActionProps) {
  return <div className="appointment-actions"><button type="button" className="secondary-button" onClick={() => onOpen(appointment)}>Editar</button>{appointment.status === 'CANCELADO' ? <button type="button" className="danger-button" onClick={() => void onDelete(appointment)}>Excluir</button> : <>{appointment.status === 'AGENDADO' && <button type="button" onClick={() => void onStatus(appointment.id, 'CONFIRMADO')}>Confirmar</button>}{mayReceiveOutcome(appointment.status) && <><button type="button" onClick={() => void onStatus(appointment.id, 'REALIZADO')}>Concluído</button><button type="button" onClick={() => void onStatus(appointment.id, 'FALTOU')}>Paciente faltou</button><button type="button" onClick={() => void onStatus(appointment.id, 'FALTOU_PROFISSIONAL')}>Profissional faltou</button><button type="button" className="danger-button" onClick={() => void onCancel(appointment)}>Cancelar</button>{appointment.recurrence_group_id && <button type="button" className="danger-button" onClick={() => void onCancelSeries(appointment)}>Encerrar recorrência</button>}</>}</>}</div>
}

function TherapistBoard({ days, selectedDayIndex, onSelectDay, appointments, professionals, filterProfessionalId, patientName, onOpenActions }: { days: Date[]; selectedDayIndex: number; onSelectDay: (index: number) => void; appointments: Appointment[]; professionals: Professional[]; filterProfessionalId: string; patientName: (id: number) => string; onOpenActions: (appointment: Appointment) => void }) {
  const selectedDate = toIsoDate(days[selectedDayIndex])
  const appointmentsOfDay = appointments.filter((item) => item.appointment_date === selectedDate)
  const professionalsOfDay = professionals.filter((professional) => filterProfessionalId ? professional.id === Number(filterProfessionalId) : appointmentsOfDay.some((item) => item.professional_id === professional.id))
  const visibleProfessionals = professionalsOfDay.length ? professionalsOfDay : professionals.filter((professional) => professional.active && (!filterProfessionalId || professional.id === Number(filterProfessionalId)))
  const startMinute = Math.min(8 * 60, ...appointmentsOfDay.map((item) => minutes(item.start_time)))
  const endMinute = Math.max(18 * 60, ...appointmentsOfDay.map((item) => minutes(item.end_time)))
  const slots = Array.from({ length: Math.max(1, Math.ceil((endMinute - startMinute) / 30)) }, (_, index) => asTime(startMinute + index * 30))

  return <div className="therapist-board"><div className="therapist-day-tabs">{days.map((day, index) => { const iso = toIsoDate(day); const count = appointments.filter((item) => item.appointment_date === iso).length; return <button type="button" className={index === selectedDayIndex ? 'selected' : ''} onClick={() => onSelectDay(index)} key={iso}><strong>{weekdays[index]}</strong><small>{formatDate(iso)} · {count} atend.</small></button> })}</div><h3>{weekdays[selectedDayIndex]} — {formatDate(selectedDate)}</h3>{visibleProfessionals.length ? <div className="therapist-grid" style={{ gridTemplateColumns: `78px repeat(${visibleProfessionals.length}, minmax(230px, 1fr))` }}><div className="grid-corner">Horário</div>{visibleProfessionals.map((professional) => <div className="therapist-header" key={professional.id}><strong>{professional.name}</strong><small>{professional.categories.join(' · ') || 'Profissional'}</small></div>)}{slots.flatMap((slot) => [<div className="time-label" key={`${slot}-time`}>{slot}</div>, ...visibleProfessionals.map((professional) => { const appointmentsAtSlot = appointmentsOfDay.filter((item) => item.professional_id === professional.id && (item.start_time.slice(0, 5) === slot || (!releasesSlot(item.status) && minutes(item.start_time) < minutes(slot) && minutes(item.end_time) > minutes(slot)))); return <div className="therapist-cell" key={`${professional.id}-${slot}`}>{appointmentsAtSlot.map((appointment) => { const startsHere = appointment.start_time.slice(0, 5) === slot; return <article className={`therapist-appointment ${appointment.status.toLowerCase()} ${startsHere ? '' : 'continues'}`} key={appointment.id}><button type="button" className="therapist-main" onClick={() => onOpenActions(appointment)}><strong>{patientName(appointment.patient_id)}</strong><span>{startsHere ? `${appointment.start_time.slice(0, 5)}–${appointment.end_time.slice(0, 5)}` : `Continua até ${appointment.end_time.slice(0, 5)}`} · {statusLabel(appointment.status)}</span></button>{startsHere && <button type="button" className="therapist-edit" onClick={() => onOpenActions(appointment)}>Editar</button>}</article> })}</div> })])}</div> : <p className="empty-day">Sem profissionais ou atendimentos para este dia.</p>}</div>
}
