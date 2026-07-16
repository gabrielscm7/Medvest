import { NavLink } from 'react-router-dom';
import { BookOpen, FileText, GraduationCap, LayoutDashboard, LogOut, Sparkles } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/simulados', label: 'Simulados', icon: BookOpen },
  { to: '/redacoes', label: 'Redação', icon: FileText },
  { to: '/flashcards', label: 'Flashcards', icon: Sparkles },
];

export function Layout({ children }: { children: React.ReactNode }) {
  const { aluno, logout } = useAuth();

  return (
    <div className="flex min-h-screen bg-gray-50">
      <aside className="w-64 bg-white border-r border-gray-200 p-4 flex flex-col">
        <div className="flex items-center gap-2 mb-8">
          <GraduationCap className="w-8 h-8 text-emerald-600" />
          <div>
            <h1 className="font-bold text-lg leading-tight">Medvest</h1>
            <p className="text-xs text-gray-500">ENEM • Medicina</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-emerald-50 text-emerald-700' : 'text-gray-600 hover:bg-gray-100'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t pt-4 space-y-2">
          <p className="text-sm text-gray-600 truncate">{aluno?.nome}</p>
          <button onClick={logout} className="flex items-center gap-2 text-sm text-red-600 hover:text-red-700 w-full">
            <LogOut className="w-4 h-4" /> Sair
          </button>
        </div>
      </aside>

      <main className="flex-1 p-6 overflow-auto">{children}</main>
    </div>
  );
}
