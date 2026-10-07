import { Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { PatientsPage } from './pages/PatientsPage'
import { AgendaPage } from './pages/AgendaPage'
import { SpreadsheetPage } from './pages/SpreadsheetPage'
import { ProfessionalsPage } from './pages/ProfessionalsPage'
import { MedicalRecordsPage } from './pages/MedicalRecordsPage'
import { AvailabilityPage } from './pages/AvailabilityPage'
import { UsersPage } from './pages/UsersPage'
import { AnamnesisPage } from './pages/AnamnesisPage'
import { CategoriesPage } from './pages/CategoriesPage'

function Layout() { const { user, logout } = useAuth(); if (!user) return <Navigate to="/login" replace />; const links = [{ to: '/', label: 'Dashboard' }, { to: '/patients', label: user.role === 'ADMIN' ? 'Pacientes' : 'Meus pacientes' }, { to: '/agenda', label: 'Agenda' }, { to: '/medical-records', label: 'Prontuários' }, { to: '/anamnesis', label: 'Anamnese' }, { to: '/availability', label: 'Disponibilidade' }]; if (user.role === 'ADMIN') links.push({ to: '/professionals', label: 'Profissionais' }, { to: '/categories', label: 'Categorias' }, { to: '/users', label: 'Usuários' }, { to: '/spreadsheet', label: 'Planilha' }); return <div className="shell"><aside><img className="brand-logo" src="/unique-icon.png" alt="Unique" /><nav>{links.map((link) => <NavLink key={link.to} to={link.to} end={link.to === '/'}>{link.label}</NavLink>)}</nav><div className="profile"><small>{user.email}</small><button className="link-button" onClick={() => void logout()}>Sair</button></div></aside><main className="content"><Outlet /></main></div> }
export default function App() { return <Routes><Route path="/login" element={<LoginPage />} /><Route element={<Layout />}><Route index element={<DashboardPage />} /><Route path="patients" element={<PatientsPage />} /><Route path="agenda" element={<AgendaPage />} /><Route path="medical-records" element={<MedicalRecordsPage />} /><Route path="anamnesis" element={<AnamnesisPage />} /><Route path="availability" element={<AvailabilityPage />} /><Route path="professionals" element={<ProfessionalsPage />} /><Route path="categories" element={<CategoriesPage />} /><Route path="users" element={<UsersPage />} /><Route path="spreadsheet" element={<SpreadsheetPage />} /></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes> }
