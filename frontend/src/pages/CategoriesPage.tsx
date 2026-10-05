import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { Category } from '../types'
import '../patients.css'

export function CategoriesPage() {
  const [items, setItems] = useState<Category[]>([])
  const [editing, setEditing] = useState<Category | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const load = async () => setItems(await api<Category[]>('/api/categories?include_inactive=true'))
  useEffect(() => { void load().catch((item: Error) => setError(item.message)) }, [])
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = event.currentTarget; const values = new FormData(form); setSaving(true); setError('')
    try { await api(editing ? `/api/categories/${editing.id}` : '/api/categories', { method: editing ? 'PATCH' : 'POST', body: JSON.stringify({ name: values.get('name'), active: editing?.active ?? true }) }); form.reset(); setEditing(null); await load() }
    catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível salvar a categoria.') } finally { setSaving(false) }
  }
  const toggleActive = async (item: Category) => { try { await api(`/api/categories/${item.id}`, { method: 'PATCH', body: JSON.stringify({ name: item.name, active: !item.active }) }); await load() } catch (errorItem) { setError(errorItem instanceof Error ? errorItem.message : 'Não foi possível atualizar a categoria.') } }
  const remove = async (item: Category) => { if (!window.confirm(`Excluir ${item.name}? Só é possível excluir categorias sem uso.`)) return; try { await api(`/api/categories/${item.id}`, { method: 'DELETE' }); await load() } catch (errorItem) { setError(errorItem instanceof Error ? errorItem.message : 'Não foi possível excluir a categoria.') } }
  return <><header className="page-heading"><div><h1>Categorias</h1><p>Especialidades disponíveis para profissionais e templates de anamnese.</p></div></header><form className="professional-form" onSubmit={submit} key={editing?.id ?? 'new'}><div className="entry-form"><input name="name" placeholder="Nome da especialidade" required defaultValue={editing?.name ?? ''} /><button disabled={saving}>{saving ? 'Salvando…' : editing ? 'Salvar categoria' : 'Adicionar categoria'}</button>{editing && <button className="secondary-button" type="button" onClick={() => setEditing(null)}>Cancelar</button>}</div></form>{error && <p className="error">{error}</p>}<section className="table-wrap"><table><thead><tr><th>Especialidade</th><th>Status</th><th>Ações</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.active ? 'Ativa' : 'Inativa'}</td><td><div className="record-actions"><button type="button" className="secondary-button" onClick={() => setEditing(item)}>Editar</button><button type="button" onClick={() => void toggleActive(item)}>{item.active ? 'Desativar' : 'Ativar'}</button><button type="button" className="danger-button" onClick={() => void remove(item)}>Excluir</button></div></td></tr>)}</tbody></table></section></> }
