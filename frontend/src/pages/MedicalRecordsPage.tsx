import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { MedicalRecord, Patient, Professional } from '../types'
import '../patients.css'
import '../records.css'

const PAGE_SIZE = 10

export function MedicalRecordsPage() {
  const { user } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [professionals, setProfessionals] = useState<Professional[]>([])
  const [records, setRecords] = useState<MedicalRecord[]>([])
  const [patientId, setPatientId] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [page, setPage] = useState(1)

  const loadRecords = async (id = patientId) => {
    setPage(1)
    if (!id) { setRecords([]); return }
    setRecords(await api<MedicalRecord[]>(`/api/medical-records?patient_id=${id}`))
  }

  useEffect(() => {
    api<Patient[]>('/api/patients').then(setPatients).catch((item: Error) => setError(item.message))
    if (user?.role === 'ADMIN') api<Professional[]>('/api/professionals').then(setProfessionals).catch((item: Error) => setError(item.message))
  }, [user?.role])
  useEffect(() => { void loadRecords().catch((item: Error) => setError(item.message)) }, [patientId])

  const totalPages = Math.max(1, Math.ceil(records.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleRecords = records.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!patientId) { setError('Selecione um paciente.'); return }
    const formElement = event.currentTarget
    const form = new FormData(formElement)
    const professionalId = user?.role === 'PROFISSIONAL' ? user.professional_id : Number(form.get('professional_id'))
    if (!professionalId) { setError('Selecione um profissional.'); return }
    setSaving(true); setError('')
    try {
      await api('/api/medical-records', { method: 'POST', body: JSON.stringify({ patient_id: Number(patientId), professional_id: professionalId, record_date: form.get('record_date'), category: form.get('category'), content: form.get('content') }) })
      formElement.reset(); await loadRecords()
    } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível criar o prontuário.') } finally { setSaving(false) }
  }

  const saveEdit = async (event: FormEvent<HTMLFormElement>, record: MedicalRecord) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setSaving(true); setError('')
    try {
      await api(`/api/medical-records/${record.id}`, { method: 'PATCH', body: JSON.stringify({ record_date: form.get('record_date'), category: form.get('category'), content: form.get('content') }) })
      setEditingId(null); await loadRecords()
    } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível editar o prontuário.') } finally { setSaving(false) }
  }

  const remove = async (record: MedicalRecord) => {
    if (!window.confirm(`Excluir definitivamente o prontuário de ${record.record_date.split('-').reverse().join('/')}?`)) return
    setError('')
    try { await api(`/api/medical-records/${record.id}`, { method: 'DELETE' }); if (editingId === record.id) setEditingId(null); await loadRecords() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível excluir o prontuário.') }
  }

  return <>
    <header className="page-heading"><div><h1>Prontuários</h1><p>Registros clínicos protegidos por vínculo profissional–paciente.</p></div></header>
    <label className="record-filter">Paciente<select value={patientId} onChange={(event) => { setPatientId(event.target.value); setEditingId(null) }}><option value="">Selecione um paciente</option>{patients.map((patient) => <option value={patient.id} key={patient.id}>{patient.name}</option>)}</select></label>
    {patientId && <>
      <form className="professional-form record-form" onSubmit={submit}>
        {user?.role === 'ADMIN' && <select name="professional_id" required defaultValue=""><option value="" disabled>Profissional responsável</option>{professionals.map((professional) => <option value={professional.id} key={professional.id}>{professional.name}</option>)}</select>}
        <input name="record_date" type="date" required /><input name="category" placeholder="Categoria do registro" required /><textarea name="content" rows={5} placeholder="Evolução ou observações clínicas" required /><button disabled={saving}>{saving ? 'Salvando…' : 'Registrar atendimento'}</button>
      </form>
      <section className="records">{visibleRecords.map((record) => editingId === record.id ? <article className="record-edit" key={record.id}><form onSubmit={(event) => void saveEdit(event, record)}><label>Data<input name="record_date" type="date" defaultValue={record.record_date} required /></label><label>Categoria<input name="category" defaultValue={record.category} required /></label><label>Registro<textarea name="content" rows={5} defaultValue={record.content} required /></label><div className="record-actions"><button disabled={saving}>{saving ? 'Salvando…' : 'Salvar alterações'}</button><button type="button" className="secondary-button" onClick={() => setEditingId(null)}>Cancelar</button></div></form></article> : <article key={record.id}><div><strong>{new Date(`${record.record_date}T12:00:00`).toLocaleDateString('pt-BR')}</strong><span>{record.category}</span></div><small className="record-author">Registrado por: {record.professional_name ?? `Profissional #${record.professional_id}`}</small><p>{record.content}</p><div className="record-actions"><button type="button" className="secondary-button" onClick={() => setEditingId(record.id)}>Editar</button><button type="button" className="danger-button" onClick={() => void remove(record)}>Excluir</button></div></article>)}{!records.length && <p>Nenhum registro para este paciente.</p>}</section>
      {records.length > 0 && <nav className="pagination" aria-label="Paginação de prontuários"><span>{records.length} registros · Página {currentPage} de {totalPages}</span><div><button type="button" className="secondary-button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Anterior</button><button type="button" className="secondary-button" disabled={currentPage === totalPages} onClick={() => setPage(currentPage + 1)}>Próxima</button></div></nav>}
    </>}{error && <p className="error">{error}</p>}
  </>
}
