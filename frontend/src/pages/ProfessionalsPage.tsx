import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { Category, Professional, User } from '../types'
import '../patients.css'
import '../professionals.css'

type ProfessionalDraft = Pick<Professional, 'name' | 'email' | 'phone'> & { categories: string[] }

const emptyDraft: ProfessionalDraft = { name: '', email: '', phone: '', categories: [] }
const PAGE_SIZE = 15

export function ProfessionalsPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'ADMIN'
  const [items, setItems] = useState<Professional[]>([])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [options, setOptions] = useState<Category[]>([])
  const [draft, setDraft] = useState<ProfessionalDraft>(emptyDraft)
  const [editing, setEditing] = useState<Professional | null>(null)
  const [page, setPage] = useState(1)
  const [createAccess, setCreateAccess] = useState(false)
  const [accessPassword, setAccessPassword] = useState('')

  const load = () => { setPage(1); return api<Professional[]>('/api/professionals').then(setItems).catch((item: Error) => setError(item.message)) }
  useEffect(() => {
    load()
    api<Category[]>('/api/categories').then(setOptions).catch((item: Error) => setError(item.message))
  }, [])

  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleItems = items.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  const updateField = (field: keyof Omit<ProfessionalDraft, 'categories'>, value: string) => setDraft((current) => ({ ...current, [field]: value }))
  const toggleCategory = (name: string) => setDraft((current) => ({ ...current, categories: current.categories.includes(name) ? current.categories.filter((item) => item !== name) : [...current.categories, name] }))
  const resetEditor = () => { setEditing(null); setDraft(emptyDraft); setCreateAccess(false); setAccessPassword(''); setError('') }
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!draft.categories.length) { setError('Selecione ao menos uma especialidade.'); return }
    if (!editing && createAccess && accessPassword.length < 12) { setError('A senha inicial do acesso deve ter pelo menos 12 caracteres.'); return }
    setSaving(true); setError('')
    const payload = { name: draft.name.trim(), email: draft.email.trim(), phone: draft.phone?.trim() || null, categories: draft.categories, active: editing?.active ?? true }
    try {
      if (editing) await api(`/api/professionals/${editing.id}`, { method: 'PATCH', body: JSON.stringify(payload) })
      else {
        const professional = await api<Professional>('/api/professionals', { method: 'POST', body: JSON.stringify(payload) })
        if (createAccess) await api<User>('/api/users', { method: 'POST', body: JSON.stringify({ professional_id: professional.id, email: payload.email, password: accessPassword }) })
      }
      resetEditor(); await load()
    } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível salvar o profissional.') }
    finally { setSaving(false) }
  }
  const startEdit = (professional: Professional) => {
    setEditing(professional)
    setDraft({ name: professional.name, email: professional.email, phone: professional.phone ?? '', categories: professional.categories })
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  const setActive = async (id: number, name: string, active: boolean) => {
    const action = active ? 'reativar' : 'desativar'
    if (!window.confirm(active ? `Reativar ${name}?` : `Desativar ${name}? O acesso ao sistema também será bloqueado.`)) return
    try {
      if (active) await api(`/api/professionals/${id}/active?active=true`, { method: 'PATCH' })
      else await api(`/api/professionals/${id}`, { method: 'DELETE' })
      await load()
    } catch (item) { setError(item instanceof Error ? item.message : `Não foi possível ${action} o profissional.`) }
  }

  return <>
    <header className="page-heading"><div><h1>Profissionais</h1><p>Equipe, especialidades e dados de contato da clínica.</p></div></header>
    {isAdmin && <section className="professional-editor">
      <div className="editor-heading"><div><h2>{editing ? `Editar ${editing.name}` : 'Novo profissional'}</h2><p>{editing ? 'Corrija e mantenha atualizados os dados de cadastro.' : 'Cadastre o profissional e selecione suas especialidades.'}</p></div>{editing && <button type="button" className="secondary-button" onClick={resetEditor}>Cancelar edição</button>}</div>
      <form className="professional-form" onSubmit={submit}>
        <div className="entry-form"><label>Nome<input value={draft.name} onChange={(event) => updateField('name', event.target.value)} required /></label><label>E-mail<input value={draft.email} onChange={(event) => updateField('email', event.target.value)} type="email" required /></label><label>Telefone<input value={draft.phone ?? ''} onChange={(event) => updateField('phone', event.target.value)} /></label></div>
        <fieldset className="category-picker"><legend>Especialidades</legend><div>{options.map((option) => <button type="button" className={draft.categories.includes(option.name) ? 'category selected' : 'category'} onClick={() => toggleCategory(option.name)} key={option.id} aria-pressed={draft.categories.includes(option.name)}>{option.name}</button>)}{!options.length && <p>Nenhuma especialidade ativa. Cadastre uma em Categorias.</p>}</div></fieldset>
        {!editing && <fieldset className="access-picker"><legend>Acesso ao sistema</legend><label className="check"><input type="checkbox" checked={createAccess} onChange={(event) => setCreateAccess(event.target.checked)} /> Criar usuário para este profissional agora</label>{createAccess && <label>Senha inicial<input type="password" value={accessPassword} onChange={(event) => setAccessPassword(event.target.value)} minLength={12} placeholder="Mínimo de 12 caracteres" required /></label>}<small>Com o acesso criado, o profissional verá apenas a própria agenda, pacientes vinculados e prontuários autorizados.</small></fieldset>}
        <div className="form-actions"><button disabled={saving}>{saving ? 'Salvando…' : editing ? 'Salvar alterações' : 'Cadastrar profissional'}</button>{editing && <button type="button" className="secondary-button" onClick={resetEditor}>Descartar</button>}</div>
      </form>
    </section>}
    {error && <p className="error">{error}</p>}
    <section className="table-wrap professionals-table"><table><thead><tr><th>Profissional</th><th>Contato</th><th>Especialidades</th><th>Status</th>{isAdmin && <th>Ações</th>}</tr></thead><tbody>{visibleItems.map((item) => <tr key={item.id}><td><strong>{item.name}</strong></td><td><span>{item.email}</span>{item.phone && <small>{item.phone}</small>}</td><td><div className="category-list">{item.categories.length ? item.categories.map((category) => <span key={category}>{category}</span>) : '—'}</div></td><td><span className={item.active ? 'status active' : 'status inactive'}>{item.active ? 'Ativo' : 'Inativo'}</span></td>{isAdmin && <td className="row-actions"><button type="button" className="secondary-button" onClick={() => startEdit(item)}>Editar</button><button type="button" className={item.active ? 'danger-button' : 'secondary-button'} onClick={() => void setActive(item.id, item.name, !item.active)}>{item.active ? 'Desativar' : 'Reativar'}</button></td>}</tr>)}{!visibleItems.length && <tr><td colSpan={isAdmin ? 5 : 4}>Nenhum profissional encontrado.</td></tr>}</tbody></table></section>
    {items.length > 0 && <nav className="pagination" aria-label="Paginação de profissionais"><span>{items.length} profissionais · Página {currentPage} de {totalPages}</span><div><button type="button" className="secondary-button" disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)}>Anterior</button><button type="button" className="secondary-button" disabled={currentPage === totalPages} onClick={() => setPage(currentPage + 1)}>Próxima</button></div></nav>}
  </>
}
