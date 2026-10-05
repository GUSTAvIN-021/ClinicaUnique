export type Role = 'ADMIN' | 'PROFISSIONAL'
export interface User { id: number; email: string; role: Role; active: boolean; professional_id: number | null }
export interface Patient { id: number; name: string; birth_date: string | null; phone: string | null; email: string | null; active: boolean; accepts_reminders: boolean; created_at: string; updated_at: string }
export interface Appointment { id: number; patient_id: number; professional_id: number; appointment_date: string; start_time: string; end_time: string; status: string; notes: string | null; recurrence_group_id: string | null }
export interface Dashboard { patients: number; active_professionals: number; today_appointments: number; week_appointments: number; missed: number; completed: number; cancelled: number; monthly_completed: number; monthly_missed: number; monthly_cancelled: number; monthly_new_patients: number }
export interface SpreadsheetEntry { id: number; entry_date: string; description: string; category: string; amount_cents: number; entry_type: 'RECEITA' | 'DESPESA'; notes: string | null }
export interface Professional { id: number; name: string; email: string; phone: string | null; categories: string[]; active: boolean }
export interface Category { id: number; name: string; active: boolean; created_at: string; updated_at: string }
export interface MedicalRecord { id: number; patient_id: number; professional_id: number; professional_name: string | null; record_date: string; category: string; content: string; created_at: string; updated_at: string }
export interface Availability { id: number; weekday: number; start_time: string; end_time: string }
export interface AnamnesisField { key: string; label: string; field_type: 'text' | 'textarea' | 'date' | 'boolean'; required: boolean }
export interface AnamnesisTemplate { id: number; category: string; fields: AnamnesisField[]; instructions: string | null; active: boolean; created_at: string; updated_at: string }
export interface AnamnesisEntry { id: number; patient_id: number; professional_id: number | null; template_key: string; answers: Record<string, string | boolean>; created_at: string; updated_at: string }
