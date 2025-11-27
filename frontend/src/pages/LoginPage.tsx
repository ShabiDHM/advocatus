// FILE: src/pages/LoginPage.tsx
// PHOENIX PROTOCOL - CLEANED (No Unused Imports)

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Mail, Lock, Loader2 } from 'lucide-react';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (err: any) {
      console.error("Login Error:", err);
      let msg = t('auth.loginFailed', 'Identifikimi dështoi.');
      if (err.response?.data?.detail) {
          if (typeof err.response.data.detail === 'string') {
              msg = err.response.data.detail;
          } else if (Array.isArray(err.response.data.detail)) {
              msg = err.response.data.detail.map((e: any) => e.msg).join(', ');
          } else {
              msg = JSON.stringify(err.response.data.detail);
          }
      }
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4">
      <div className="max-w-md w-full space-y-8 p-8 bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge shadow-2xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white">{t('auth.loginTitle', 'Hyni në Juristi AI')}</h2>
          <p className="mt-2 text-sm text-text-secondary">{t('auth.loginSubtitle', 'Menaxhoni çështjet ligjore me inteligjencë.')}</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">{t('auth.email', 'Email')}</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Mail className="h-5 w-5 text-text-secondary" /></div>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="block w-full pl-10 px-3 py-2 bg-background-dark/50 border border-glass-edge rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-start outline-none" placeholder="emri@shembull.com" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">{t('auth.password', 'Fjalëkalimi')}</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Lock className="h-5 w-5 text-text-secondary" /></div>
                <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} className="block w-full pl-10 px-3 py-2 bg-background-dark/50 border border-glass-edge rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-start outline-none" placeholder="••••••••" />
              </div>
            </div>
          </div>

          {error && <div className="text-red-400 text-sm text-center bg-red-900/20 p-2 rounded-lg border border-red-500/30">{error}</div>}

          <button type="submit" disabled={isSubmitting} className="w-full flex justify-center py-2.5 px-4 rounded-xl text-white bg-gradient-to-r from-primary-start to-primary-end font-medium shadow-lg hover:opacity-90 disabled:opacity-50 transition-all">
            {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : t('auth.loginButton', 'Hyni')}
          </button>
        </form>
        <div className="text-center text-sm">
          <span className="text-text-secondary">{t('auth.noAccount', 'Nuk keni llogari?')} </span>
          <Link to="/register" className="font-medium text-primary-start hover:text-primary-end transition-colors">{t('auth.registerLink', 'Regjistrohu')}</Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;