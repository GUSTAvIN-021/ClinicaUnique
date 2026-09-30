export type Role = 'ADMIN' | 'PROFISSIONAL'
export interface User { id: number; email: string; role: Role; active: boolean; professional_id: number | null }
export interface Patient { id: number; name: string; birth_date: string | null; phone: string | null; email: string | null; active: boolean; accepts_reminders: boolean; created_at: string; updated_at: string }
export interface Appointment { id: number; patient_id: number; professional_id: number; appointment_date: string; start_time: string; end_time: string; status: string; notes: string | null }
export interface Dashboard { patients: number; active_professionals: number; today_appointments: number; week_appointments: number; missed: number; completed: number; cancelled: number }
export interface SpreadsheetEntry { id: number; entry_date: string; description: string; category: string; amount_cents: number; entry_type: 'RECEITA' | 'DESPESA'; notes: string | null }
export interface Professional { id: number; name: string; email: string; phone: string | null; categories: string[]; active: boolean }
export interface MedicalRecord { id: number; patient_id: number; professional_id: number; record_date: string; category: string; content: string; created_at: string; updated_at: string }
export interface Availability { id: number; weekday: number; start_time: string; end_time: string }
