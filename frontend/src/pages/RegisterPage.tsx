// FILE: src/pages/RegisterPage.tsx
// PHOENIX PROTOCOL - REGISTER PAGE V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, btn-primary, etc.
// 2. Clean, authoritative layout with structured spacing.
// 3. Preserved all registration logic and success state with professional messaging.

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { User, Mail, Lock, Loader2, ArrowRight, ShieldAlert, Sparkles } from 'lucide-react';
import { RegisterRequest } from '../data/types';

const RegisterPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (username.length < 3) {
      setError(t('auth.usernameTooShort'));
      return;
    }
    if (password.length < 8) {
      setError(t('auth.passwordTooShort'));
      return;
    }

    setIsSubmitting(true);

    const payload: RegisterRequest = {
      email,
      password,
      username,
    };

    try {
      await apiService.register(payload);
      setIsSuccess(true);
    } catch (err: any) {
      console.error('Registration Error:', err.response?.data);

      let msg = t('auth.registerFailed');
      if (err.response?.data?.detail) {
        if (typeof err.response.data.detail === 'string') {
          msg = err.response.data.detail;
        } else if (Array.isArray(err.response.data.detail)) {
          msg = err.response.data.detail.map((e: any) => `${e.loc[1]}: ${e.msg}`).join(', ');
        } else {
          msg = JSON.stringify(err.response.data.detail);
        }
      }
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-canvas px-4 font-sans selection:bg-primary-start/30">
        <div className="glass-panel max-w-md w-full p-10 rounded-2xl border border-main text-center shadow-2xl transition-all duration-300">
          <div className="w-24 h-24 bg-gradient-to-br from-primary-start/20 to-primary-end/20 rounded-full flex items-center justify-center mx-auto mb-8 ring-1 ring-primary-start/30">
            <Sparkles className="w-12 h-12 text-primary-start" />
          </div>

          <h2 className="text-3xl font-semibold tracking-tight text-text-primary mb-4">
            {t('auth.welcomeTitle', 'Mirë se erdhët në të ardhmen')}
          </h2>

          <p className="text-text-secondary mb-10 leading-relaxed text-lg">
            {t(
              'auth.welcomeMessage',
              'Llogaria juaj është krijuar. Ndërsa ekipi ynë verifikon të dhënat, ju jeni një hap më afër bashkimit të ekspertizës njerëzore me fuqinë e të dhënave për të transformuar praktikën tuaj ligjore.'
            )}
          </p>

          <Link
            to="/login"
            className="btn-primary inline-flex items-center px-8 py-3 rounded-xl font-semibold shadow-lg hover:shadow-primary-start/20 transition-all active:scale-[0.98]"
          >
            {t('auth.backToLogin', 'Kthehu te Kyçja')} <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4 font-sans selection:bg-primary-start/30">
      <div className="glass-panel max-w-md w-full p-8 rounded-2xl border border-main shadow-2xl transition-all duration-300">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-semibold tracking-tight text-text-primary mb-2">
            {t('auth.registerTitle')}
          </h2>
          <p className="text-text-secondary">{t('auth.registerSubtitle')}</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">
              {t('account.username')}
            </label>
            <div className="relative">
              <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted pointer-events-none" />
              <input
                type="text"
                required
                minLength={3}
                placeholder={t('auth.usernamePlaceholder')}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="glass-input w-full pl-10 pr-4 py-3 rounded-xl border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">
              {t('account.email')}
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted pointer-events-none" />
              <input
                type="email"
                required
                placeholder={t('auth.emailPlaceholder')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="glass-input w-full pl-10 pr-4 py-3 rounded-xl border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">
              {t('auth.password')}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted pointer-events-none" />
              <input
                type="password"
                required
                minLength={8}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="glass-input w-full pl-10 pr-4 py-3 rounded-xl border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all"
              />
            </div>
            <p className="text-[10px] text-text-muted text-right font-medium">
              {t('auth.passwordMinChars')}
            </p>
          </div>

          {error && (
            <div className="flex items-start gap-3 bg-danger-start/10 border border-danger-start/20 rounded-xl p-3 text-danger-start text-sm font-medium">
              <ShieldAlert className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn-primary w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 shadow-lg hover:shadow-primary-start/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>{t('auth.processing')}</span>
              </>
            ) : (
              t('auth.createAccount')
            )}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-text-secondary">
          {t('auth.hasAccount')}{' '}
          <Link
            to="/login"
            className="font-semibold text-primary-start hover:text-primary-end transition-colors hover:underline"
          >
            {t('auth.signInLink')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;