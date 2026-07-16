import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';
import Login from './pages/Login';
import Register from './pages/Register';
import DashboardPage from './pages/Dashboard';
import Simulados from './pages/Simulados';
import SimuladoDetalhe from './pages/SimuladoDetalhe';
import Redacoes from './pages/Redacoes';
import FlashcardsPage from './pages/Flashcards';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<ProtectedRoute><Layout><DashboardPage /></Layout></ProtectedRoute>} />
          <Route path="/simulados" element={<ProtectedRoute><Layout><Simulados /></Layout></ProtectedRoute>} />
          <Route path="/simulados/:id" element={<ProtectedRoute><Layout><SimuladoDetalhe /></Layout></ProtectedRoute>} />
          <Route path="/redacoes" element={<ProtectedRoute><Layout><Redacoes /></Layout></ProtectedRoute>} />
          <Route path="/flashcards" element={<ProtectedRoute><Layout><FlashcardsPage /></Layout></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
