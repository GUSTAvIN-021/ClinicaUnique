import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../services/api'
import { useAuth } from '../contexts/AuthContext'
import type { AnamnesisEntry, AnamnesisField, AnamnesisTemplate, Category, Patient } from '../types'
import '../patients.css'
import '../anamnesis.css'

const defaultFields: AnamnesisField[] = [
  { key: 'queixa_principal', label: 'Queixa principal', field_type: 'textarea', required: true },
  { key: 'historico', label: 'Histórico relevante', field_type: 'textarea', required: false },
]
const fieldKey = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'campo'

export function AnamnesisPage() {
  const { user } = useAuth()
  const [patients, setPatients] = useState<Patient[]>([])
  const [templates, setTemplates] = useState<AnamnesisTemplate[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [entries, setEntries] = useState<AnamnesisEntry[]>([])
  const [patientId, setPatientId] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [answers, setAnswers] = useState<Record<string, string | boolean>>({})
  const [editingEntry, setEditingEntry] = useState<AnamnesisEntry | null>(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [draftCategory, setDraftCategory] = useState('')
  const [draftFields, setDraftFields] = useState<AnamnesisField[]>(defaultFields)
  const [editingTemplate, setEditingTemplate] = useState<AnamnesisTemplate | null>(null)

  const selectedTemplate = templates.find((item) => item.id === Number(templateId))
  const activeTemplates = templates.filter((item) => item.active || item.id === selectedTemplate?.id)
  const loadTemplates = async () => setTemplates(await api<AnamnesisTemplate[]>('/api/anamnesis/templates'))
  const loadEntries = async (id = patientId) => { if (!id) { setEntries([]); return }; setEntries(await api<AnamnesisEntry[]>(`/api/anamnesis?patient_id=${id}`)) }

  useEffect(() => { api<Patient[]>('/api/patients').then(setPatients).catch((item: Error) => setError(item.message)); api<Category[]>('/api/categories').then(setCategories).catch((item: Error) => setError(item.message)); void loadTemplates().catch((item: Error) => setError(item.message)) }, [])
  useEffect(() => { void loadEntries().catch((item: Error) => setError(item.message)) }, [patientId])
  useEffect(() => { if (!editingEntry) setAnswers({}) }, [templateId])

  const saveEntry = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!patientId || !selectedTemplate) { setError('Selecione o paciente e o template de anamnese.'); return }
    setSaving(true); setError('')
    try {
      if (editingEntry) await api(`/api/anamnesis/${editingEntry.id}`, { method: 'PATCH', body: JSON.stringify({ answers }) })
      else await api('/api/anamnesis', { method: 'POST', body: JSON.stringify({ patient_id: Number(patientId), professional_id: user?.role === 'PROFISSIONAL' ? user.professional_id : null, template_key: selectedTemplate.category, answers }) })
      setAnswers({}); setEditingEntry(null); await loadEntries()
    } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível salvar a anamnese.') } finally { setSaving(false) }
  }
  const selectEntry = (entry: AnamnesisEntry) => {
    const template = templates.find((item) => item.category === entry.template_key)
    if (!template) { setError('O template original desta anamnese não está mais disponível.'); return }
    setTemplateId(String(template.id)); setAnswers(entry.answers); setEditingEntry(entry)
  }
  const removeEntry = async (entry: AnamnesisEntry) => {
    if (!window.confirm('Excluir esta anamnese?')) return
    try { await api(`/api/anamnesis/${entry.id}`, { method: 'DELETE' }); if (editingEntry?.id === entry.id) { setEditingEntry(null); setAnswers({}) }; await loadEntries() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível excluir a anamnese.') }
  }
  const addDraftField = () => setDraftFields((items) => [...items, { key: `campo_${items.length + 1}`, label: '', field_type: 'text', required: false }])
  const updateDraftField = (index: number, value: Partial<AnamnesisField>) => setDraftFields((items) => items.map((item, itemIndex) => itemIndex === index ? { ...item, ...value } : item))
  const saveTemplate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!draftCategory || draftFields.some((item) => !item.label || !item.key)) { setError('Preencha a especialidade e todos os campos do template.'); return }
    setSaving(true); setError('')
    try { const payload = { category: draftCategory, fields: draftFields, active: true }; await api(editingTemplate ? `/api/anamnesis/templates/${editingTemplate.id}` : '/api/anamnesis/templates', { method: editingTemplate ? 'PATCH' : 'POST', body: JSON.stringify(payload) }); setDraftCategory(''); setDraftFields(defaultFields); setEditingTemplate(null); await loadTemplates() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível salvar o template.') } finally { setSaving(false) }
  }
  const editTemplate = (template: AnamnesisTemplate) => { setEditingTemplate(template); setDraftCategory(template.category); setDraftFields(template.fields) }
  const removeTemplate = async (template: AnamnesisTemplate) => { if (!window.confirm(`Excluir o template de ${template.category}? As anamneses já preenchidas serão preservadas.`)) return; try { await api(`/api/anamnesis/templates/${template.id}`, { method: 'DELETE' }); if (templateId === String(template.id)) setTemplateId(''); await loadTemplates() } catch (item) { setError(item instanceof Error ? item.message : 'Não foi possível excluir o template.') } }
  const templateCategories = useMemo(() => categories.filter((category) => !templates.some((item) => item.category === category.name && item.id !== editingTemplate?.id)), [categories, templates, editingTemplate])

  return <>
    <header className="page-heading"><div><h1>Anamnese</h1><p>Questionários estruturados por especialidade, protegidos pelo vínculo do paciente.</p></div></header>
    {user?.role === 'ADMIN' && <details className="registration template-manager"><summary>{editingTemplate ? `Editando template: ${editingTemplate.category}` : 'Gerenciar templates de anamnese'}</summary><form onSubmit={saveTemplate}><label className="field">Especialidade<select value={draftCategory} onChange={(event) => setDraftCategory(event.target.value)} required><option value="">Selecione</option>{templateCategories.map((category) => <option value={category.name} key={category.id}>{category.name}</option>)}</select></label><div className="template-fields"><strong>Campos do formulário</strong>{draftFields.map((field, index) => <div className="template-field" key={`${field.key}-${index}`}><input value={field.label} placeholder="Nome do campo" onChange={(event) => updateDraftField(index, { label: event.target.value, key: fieldKey(event.target.value) })} required /><select value={field.field_type} onChange={(event) => updateDraftField(index, { field_type: event.target.value as AnamnesisField['field_type'] })}><option value="text">Texto curto</option><option value="textarea">Texto longo</option><option value="date">Data</option><option value="boolean">Sim ou não</option></select><label className="check"><input type="checkbox" checked={field.required} onChange={(event) => updateDraftField(index, { required: event.target.checked })} /> Obrigatório</label>{draftFields.length > 1 && <button type="button" className="danger-button" onClick={() => setDraftFields((items) => items.filter((_, itemIndex) => itemIndex !== index))}>Remover</button>}</div>)}<button type="button" className="secondary-button" onClick={addDraftField}>Adicionar campo</button></div><div className="record-actions"><button disabled={saving}>{saving ? 'Salvando…' : editingTemplate ? 'Salvar template' : 'Criar template'}</button>{editingTemplate && <button type="button" className="secondary-button" onClick={() => { setEditingTemplate(null); setDraftCategory(''); setDraftFields(defaultFields) }}>Cancelar edição</button>}</div></form><section className="template-list">{templates.map((template) => <article key={template.id}><strong>{template.category}</strong><span>{template.fields.length} campos · {template.active ? 'Ativo' : 'Inativo'}</span><div className="record-actions"><button type="button" className="secondary-button" onClick={() => editTemplate(template)}>Editar</button><button type="button" className="danger-button" onClick={() => void removeTemplate(template)}>Excluir</button></div></article>)}</section></details>}
    <label className="record-filter">Paciente<select value={patientId} onChange={(event) => { setPatientId(event.target.value); setEditingEntry(null); setAnswers({}) }}><option value="">Selecione um paciente</option>{patients.map((patient) => <option value={patient.id} key={patient.id}>{patient.name}</option>)}</select></label>
    {patientId && <section className="anamnesis-workspace"><form className="anamnesis-form" onSubmit={saveEntry}><label className="field">Template<select value={templateId} onChange={(event) => { setTemplateId(event.target.value); setEditingEntry(null) }} required><option value="">Selecione a especialidade</option>{activeTemplates.map((template) => <option value={template.id} key={template.id}>{template.category}</option>)}</select></label>{selectedTemplate && <>{editingEntry && <p className="editing-note">Editando anamnese registrada em {new Date(editingEntry.created_at).toLocaleDateString('pt-BR')}.</p>}{selectedTemplate.fields.map((field) => <label className="field" key={field.key}>{field.label}{field.field_type === 'textarea' ? <textarea value={String(answers[field.key] ?? '')} onChange={(event) => setAnswers({ ...answers, [field.key]: event.target.value })} required={field.required} rows={4} /> : field.field_type === 'boolean' ? <span className="check"><input type="checkbox" checked={answers[field.key] === true} onChange={(event) => setAnswers({ ...answers, [field.key]: event.target.checked })} /> Sim</span> : <input type={field.field_type} value={String(answers[field.key] ?? '')} onChange={(event) => setAnswers({ ...answers, [field.key]: event.target.value })} required={field.required} />}</label>)}<div className="record-actions"><button disabled={saving}>{saving ? 'Salvando…' : editingEntry ? 'Salvar alterações' : 'Registrar anamnese'}</button>{editingEntry && <button type="button" className="secondary-button" onClick={() => { setEditingEntry(null); setAnswers({}) }}>Nova anamnese</button>}</div></>}</form><aside className="anamnesis-history"><h2>Histórico</h2>{entries.map((entry) => <article key={entry.id}><strong>{entry.template_key}</strong><small>{new Date(entry.created_at).toLocaleDateString('pt-BR')}</small><div className="record-actions"><button type="button" className="secondary-button" onClick={() => selectEntry(entry)}>Abrir</button><button type="button" className="danger-button" onClick={() => void removeEntry(entry)}>Excluir</button></div></article>)}{!entries.length && <p>Nenhuma anamnese preenchida.</p>}</aside></section>}{error && <p className="error">{error}</p>}
  </>
}
