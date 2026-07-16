import { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import { me, type Aluno } from '../api/auth';

interface AuthContextType {
  aluno: Aluno | null;
  token: string | null;
  loading: boolean;
  setAuth: (token: string, aluno: Aluno) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [aluno, setAluno] = useState<Aluno | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      me().then(setAluno).catch(() => { localStorage.removeItem('token'); setToken(null); })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const setAuth = (t: string, a: Aluno) => {
    localStorage.setItem('token', t);
    setToken(t);
    setAluno(a);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setAluno(null);
  };

  return (
    <AuthContext.Provider value={{ aluno, token, loading, setAuth, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
