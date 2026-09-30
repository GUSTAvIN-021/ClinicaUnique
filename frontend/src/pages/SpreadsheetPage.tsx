import { FormEvent, useEffect, useState } from 'react'
import { api } from '../services/api'
import type { SpreadsheetEntry } from '../types'
import '../spreadsheet.css'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

export function SpreadsheetPage() {
  const [entries, setEntries] = useState<SpreadsheetEntry[]>([]); const [error, setError] = useState(''); const [saving, setSaving] = useState(false)
  const load = () => api<SpreadsheetEntry[]>('/api/spreadsheet').then(setEntries).catch((e: Error) => setError(e.message))
  useEffect(() => { load() }, [])
  const submit = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const formElement = event.currentTarget; setSaving(true); setError(''); const form = new FormData(formElement); try { await api('/api/spreadsheet', { method: 'POST', body: JSON.stringify({ entry_date: form.get('entry_date'), description: form.get('description'), category: form.get('category'), entry_type: form.get('entry_type'), amount_cents: Math.round(Number(form.get('amount')) * 100), notes: form.get('notes') || null }) }); formElement.reset(); await load() } catch (e) { setError(e instanceof Error ? e.message : 'Não foi possível salvar.') } finally { setSaving(false) } }
  const total = entries.reduce((sum, item) => sum + (item.entry_type === 'RECEITA' ? item.amount_cents : -item.amount_cents), 0)
  return <><header className="page-heading"><div><h1>Planilha administrativa</h1><p>Controle financeiro operacional.</p></div><strong className={total >= 0 ? 'positive' : 'negative'}>{currency.format(total / 100)}</strong></header><form className="entry-form" onSubmit={submit}><input name="entry_date" type="date" required /><input name="description" placeholder="Descrição" required /><input name="category" placeholder="Categoria" required /><select name="entry_type"><option value="RECEITA">Receita</option><option value="DESPESA">Despesa</option></select><input name="amount" type="number" step="0.01" min="0.01" placeholder="Valor" required /><button disabled={saving}>{saving ? 'Salvando…' : 'Adicionar'}</button></form>{error && <p className="error">{error}</p>}<section className="table-wrap"><table><thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Tipo</th><th>Valor</th></tr></thead><tbody>{entries.map((item) => <tr key={item.id}><td>{new Date(`${item.entry_date}T12:00:00`).toLocaleDateString('pt-BR')}</td><td>{item.description}</td><td>{item.category}</td><td>{item.entry_type}</td><td className={item.entry_type === 'RECEITA' ? 'positive' : 'negative'}>{currency.format(item.amount_cents / 100)}</td></tr>)}</tbody></table></section></> }
