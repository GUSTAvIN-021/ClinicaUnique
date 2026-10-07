import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Patient, Professional } from '../types'
import '../spreadsheet.css'
import '../patients.css'

const PAGE_SIZE = 15

export function PatientsPage() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [professionals, setProfessionals] = useState<Professional[]>([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [selectedProfessionals, setSelectedProfessionals] = useState<number[]>([])
  const [page, setPage] = useState(1)

  const load = (q = '') => {
    setPage(1)
    return api<Patient[]>(`/api/patients${q ? `?q=${encodeURIComponent(q)}` : ''}`)
      .then(setPatients)
      .catch((item: Error) => setError(item.message))
  }

  useEffect(() => {
    void load()
    api<Professional[]>('/api/professionals').then(setProfessionals).catch((item: Error) => setError(item.message))
  }, [])

  const totalPages = Math.max(1, Math.ceil(patients.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visiblePatients = patients.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const toggleProfessional = (id: number) => setSelectedProfessionals((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])
  const deactivate = async (id: number, name: string) => {
    if (!window.confirm(`Desativar ${name}? O histórico clínico será preservado.`)) return
    try { await api(`/api/patients/${id}`, { method: 'DELETE' }); await load(query) }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível desativar o paciente.') }
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formElement = event.currentTarget
    setSaving(true); setError('')
    const form = new FormData(formElement)
    try {
      const patient = await api<Patient>('/api/patients', { method: 'POST', body: JSON.stringify({
        name: form.get('name'), birth_date: form.get('birth_date') || null, cpf: form.get('cpf') || null,
        phone: form.get('phone') || null, email: form.get('email') || null, guardian_name: form.get('guardian_name') || null,
        guardian_phone: form.get('guardian_phone') || null, address: form.get('address') || null, notes: form.get('notes') || null,
        accepts_reminders: form.get('accepts_reminders') === 'on', active: true,
      }) })
      await Promise.all(selectedProfessionals.map((professionalId) => api<void>(`/api/professionals/${professionalId}/patients/${patient.id}`, { method: 'PUT' })))
      formElement.reset(); setSelectedProfessionals([]); await load()
    } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível cadastrar o paciente.') }
    finally { setSaving(false) }
  }

  return <>
    <header className="page-heading"><div><h1>Pacientes</h1><p>Cadastros, vínculos e acompanhamento.</p></div></header>
    <details className="registration"><summary>Cadastrar paciente</summary><form className="professional-form" onSubmit={submit}>
      <div className="entry-form"><input name="name" placeholder="Nome completo" required /><input name="birth_date" type="date" aria-label="Data de nascimento" /><input name="cpf" placeholder="CPF" /><input name="phone" placeholder="Telefone" /><input name="email" type="email" placeholder="E-mail" /><input name="guardian_name" placeholder="Responsável" /><input name="guardian_phone" placeholder="Telefone do responsável" /><input name="address" placeholder="Endereço" /></div>
      <textarea name="notes" placeholder="Observações" rows={3} /><label className="check"><input name="accepts_reminders" type="checkbox" defaultChecked /> Aceita lembretes</label>
      <fieldset className="category-picker"><legend>Profissionais vinculados</legend><div>{professionals.map((professional) => <button type="button" className={selectedProfessionals.includes(professional.id) ? 'category selected' : 'category'} onClick={() => toggleProfessional(professional.id)} key={professional.id} aria-pressed={selectedProfessionals.includes(professional.id)}>{professional.name}</button>)}</div></fieldset>
      <button disabled={saving}>{saving ? 'Salvando…' : 'Cadastrar paciente'}</button>
    </form></details>
    <form className="toolbar" onSubmit={(event) => { event.preventDefault(); void load(query) }}><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por nome" /><button>Buscar</button></form>
    {error && <p className="error">{error}</p>}
    <section className="table-wrap"><table><thead><tr><th>Nome</th><th>Telefone</th><th>E-mail</th><th>Status</th><th>Ações</th></tr></thead><tbody>
      {visiblePatients.map((patient) => <tr key={patient.id}><td>{patient.name}</td><td>{patient.phone ?? '—'}</td><td>{patient.email ?? '—'}</td><td>{patient.active ? 'Ativo' : 'Inativo'}</td><td>{patient.active && <button className="danger-button" onClick={() => void deactivate(patient.id, patient.name)}>Desativar</button>}</td></tr>)}
      {!visiblePatients.length && <tr><td colSpan={5}>Nenhum paciente encontrado.</td></tr>}
    </tbody></table></section>
    <Pagination currentPage={currentPage} totalPages={totalPages} totalItems={patients.length} onPageChange={setPage} label="pacientes" />
  </>
}

function Pagination({ currentPage, totalPages, totalItems, onPageChange, label }: { currentPage: number; totalPages: number; totalItems: number; onPageChange: (page: number) => void; label: string }) {
  if (!totalItems) return null
  return <nav className="pagination" aria-label={`Paginação de ${label}`}><span>{totalItems} {label} · Página {currentPage} de {totalPages}</span><div><button type="button" className="secondary-button" disabled={currentPage === 1} onClick={() => onPageChange(currentPage - 1)}>Anterior</button><button type="button" className="secondary-button" disabled={currentPage === totalPages} onClick={() => onPageChange(currentPage + 1)}>Próxima</button></div></nav>
}
