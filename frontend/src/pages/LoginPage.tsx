// FILE: src/pages/LoginPage.tsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { Mail, Lock, Loader2, ArrowRight } from 'lucide-react';

const LoginPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
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
    } catch (err) {
      setError(t('auth.loginFailed', 'Identifikimi dështoi. Kontrolloni kredencialet.'));
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
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-text-secondary" />
                </div>
                <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                  className="block w-full pl-10 px-3 py-2 bg-background-dark/50 border border-glass-edge rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-start focus:border-transparent outline-none transition-all"
                  placeholder="emri@shembull.com"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">{t('auth.password', 'Fjalëkalimi')}</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-text-secondary" />
                </div>
                <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 px-3 py-2 bg-background-dark/50 border border-glass-edge rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-start focus:border-transparent outline-none transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>

          {error && <div className="text-red-400 text-sm text-center bg-red-900/20 p-2 rounded-lg border border-red-500/30">{error}</div>}

          <button type="submit" disabled={isSubmitting}
            className="group relative w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-medium rounded-xl text-white bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-start disabled:opacity-50 shadow-lg glow-primary transition-all"
          >
            {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : (
              <span className="flex items-center">
                {t('auth.loginButton', 'Hyni')} <ArrowRight className="ml-2 h-4 w-4 group-hover:translate-x-1 transition-transform" />
              </span>
            )}
          </button>
        </form>
        <div className="text-center text-sm">
          <span className="text-text-secondary">{t('auth.noAccount', 'Nuk keni llogari?')} </span>
          <Link to="/register" className="font-medium text-primary-start hover:text-primary-end transition-colors">
            {t('auth.registerLink', 'Regjistrohu')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;