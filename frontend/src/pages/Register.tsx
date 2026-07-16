import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { GraduationCap } from 'lucide-react';
import { register } from '../api/auth';

export default function Register() {
  const [form, setForm] = useState({ nome: '', email: '', senha: '', meta_instituicao: '' });
  const [erro, setErro] = useState('');
  const navigate = useNavigate();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro('');
    try {
      await register(form);
      navigate('/login');
    } catch (err: any) {
      setErro(err.message || 'Erro ao cadastrar');
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 to-green-100">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="flex items-center justify-center gap-2 mb-8">
          <GraduationCap className="w-10 h-10 text-emerald-600" />
          <h1 className="text-2xl font-bold">Medvest</h1>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
            <input type="text" value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
            <input type="password" value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Instituição alvo (opcional)</label>
            <input type="text" value={form.meta_instituicao} onChange={(e) => setForm({ ...form, meta_instituicao: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-emerald-500 outline-none" />
          </div>
          {erro && <p className="text-red-600 text-sm">{erro}</p>}
          <button type="submit" className="w-full py-2 px-4 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium transition-colors">
            Cadastrar
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-4">
          Já tem conta? <Link to="/login" className="text-emerald-600 hover:underline">Entrar</Link>
        </p>
      </div>
    </div>
  );
}
