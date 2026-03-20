// FILE: src/pages/LoginPage.tsx
// PHOENIX PROTOCOL - LOGIN PAGE V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Semantic classes: bg-surface, border-main, text-text-primary, btn-primary, glass-panel.
// 2. Prestige layout: structured spacing, clean typography, subtle shadow.
// 3. All auth logic preserved.

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTranslation } from 'react-i18next';
import { User, Lock, Loader2 } from 'lucide-react';

const LoginPage: React.FC = () => {
  const [identity, setIdentity] = useState('');
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
      await login(identity, password);
      navigate('/dashboard');
    } catch (err: any) {
      console.error('Login Error:', err);
      let msg = t('auth.loginFailed');
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
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4 font-sans selection:bg-primary-start/30">
      {/* Prestige: structured container with subtle border and shadow */}
      <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-main shadow-2xl transition-all duration-300">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold tracking-tight text-text-primary">
            {t('auth.loginTitle')}
          </h1>
          <p className="mt-2 text-sm text-text-secondary">
            {t('auth.loginSubtitle')}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-4">
            <div>
              <label htmlFor="identity" className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">
                {t('auth.usernameOrEmail')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <User className="h-5 w-5 text-text-muted" />
                </div>
                <input
                  id="identity"
                  type="text"
                  required
                  value={identity}
                  onChange={(e) => setIdentity(e.target.value)}
                  className="glass-input block w-full pl-10 pr-4 py-3 rounded-xl border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all"
                  placeholder={t('auth.usernameOrEmailPlaceholder')}
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-semibold uppercase tracking-wider text-text-secondary mb-1">
                {t('auth.password')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-text-muted" />
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="glass-input block w-full pl-10 pr-4 py-3 rounded-xl border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all"
                  placeholder="••••••••"
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="text-danger-start text-sm text-center bg-danger-start/10 p-3 rounded-xl border border-danger-start/20 font-medium">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-3 rounded-xl font-semibold shadow-lg hover:shadow-primary-start/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? <Loader2 className="animate-spin h-5 w-5 mx-auto" /> : t('auth.loginButton')}
          </button>
        </form>

        <div className="text-center text-sm mt-6 pt-4 border-t border-main">
          <span className="text-text-secondary">{t('auth.noAccount')} </span>
          <Link
            to="/register"
            className="font-semibold text-primary-start hover:text-primary-end transition-colors hover:underline"
          >
            {t('auth.registerLink')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;