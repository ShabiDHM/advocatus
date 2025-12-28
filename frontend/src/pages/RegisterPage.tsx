// FILE: src/pages/RegisterPage.tsx
// PHOENIX PROTOCOL - REGISTER PAGE V3.0 (GLASS STYLE)
// 1. VISUALS: Full Glassmorphism adoption (glass-high, glass-input).
// 2. LAYOUT: Ambient background and consistent spacing.
// 3. MESSAGING: Retained inspirational messaging for the success state.

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
        username
    };

    try {
      await apiService.register(payload);
      setIsSuccess(true);
    } catch (err: any) {
      console.error("Registration Error:", err.response?.data);
      
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
        <div className="min-h-screen flex items-center justify-center bg-background-dark px-4 relative overflow-hidden font-sans selection:bg-primary-start/30">
            {/* Ambient Background */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-emerald-500/20 rounded-full blur-[100px] opacity-40 animate-pulse-slow"></div>
                <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
            </div>

            <div className="glass-high max-w-md w-full p-10 rounded-3xl border border-white/10 text-center shadow-2xl relative z-10 animate-in fade-in zoom-in-95 duration-500">
                <div className="w-24 h-24 bg-gradient-to-br from-emerald-400/20 to-emerald-600/20 rounded-full flex items-center justify-center mx-auto mb-8 shadow-[0_0_30px_rgba(52,211,153,0.3)] ring-1 ring-emerald-500/30">
                    <Sparkles className="w-12 h-12 text-emerald-400" />
                </div>
                
                <h2 className="text-3xl font-bold text-white mb-4 tracking-tight">
                    {t('auth.welcomeTitle', 'Mirë se erdhët në të ardhmen')}
                </h2>
                
                <p className="text-gray-300 mb-10 leading-relaxed text-lg">
                    {t('auth.welcomeMessage', 'Llogaria juaj është krijuar. Ndërsa ekipi ynë verifikon të dhënat, ju jeni një hap më afër bashkimit të ekspertizës njerëzore me fuqinë e të dhënave për të transformuar praktikën tuaj ligjore.')}
                </p>
                
                <Link to="/login" className="inline-flex items-center px-8 py-4 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-white rounded-xl font-bold transition-all shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/40 hover:-translate-y-1">
                    {t('auth.backToLogin', 'Kthehu te Kyçja')} <ArrowRight className="ml-2 w-5 h-5" />
                </Link>
            </div>
        </div>
      );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4 relative overflow-hidden font-sans selection:bg-primary-start/30">
        {/* Ambient Background */}
        <div className="fixed inset-0 pointer-events-none">
            <div className="absolute top-[-10%] right-[-10%] w-[500px] h-[500px] bg-primary-start/20 rounded-full blur-[100px] opacity-40 animate-pulse-slow"></div>
            <div className="absolute bottom-[-10%] left-[-10%] w-[500px] h-[500px] bg-secondary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
        </div>

      <div className="glass-high max-w-md w-full p-8 rounded-3xl shadow-2xl relative z-10 animate-in fade-in zoom-in-95 duration-300 border border-white/10">
        <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-white mb-2 tracking-tight">{t('auth.registerTitle')}</h2>
            <p className="text-text-secondary">{t('auth.registerSubtitle')}</p>
        </div>

        <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 ml-1 uppercase tracking-wider">{t('account.username')}</label>
                <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 pointer-events-none" />
                    <input 
                        type="text" 
                        required 
                        minLength={3}
                        placeholder={t('auth.usernamePlaceholder')}
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        className="glass-input w-full pl-10 pr-4 py-3 rounded-xl"
                    />
                </div>
            </div>

            <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 ml-1 uppercase tracking-wider">{t('account.email')}</label>
                <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 pointer-events-none" />
                    <input 
                        type="email" 
                        required 
                        placeholder={t('auth.emailPlaceholder')}
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        className="glass-input w-full pl-10 pr-4 py-3 rounded-xl"
                    />
                </div>
            </div>

            <div className="space-y-1.5">
                <label className="text-xs font-bold text-gray-400 ml-1 uppercase tracking-wider">{t('auth.password')}</label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500 pointer-events-none" />
                    <input 
                        type="password" 
                        required 
                        minLength={8}
                        placeholder="••••••••"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        className="glass-input w-full pl-10 pr-4 py-3 rounded-xl"
                    />
                </div>
                <p className="text-[10px] text-gray-500 text-right font-medium">{t('auth.passwordMinChars')}</p>
            </div>
            
            {error && (
                <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-red-300 text-sm font-medium">
                    <ShieldAlert className="w-5 h-5 shrink-0" />
                    <span>{error}</span>
                </div>
            )}

            <button 
                type="submit" 
                disabled={isSubmitting} 
                className="w-full py-3 bg-gradient-to-r from-primary-start to-primary-end hover:opacity-90 text-white rounded-xl font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-primary-start/20 active:scale-95"
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

        <div className="mt-6 text-center text-sm text-gray-400">
            {t('auth.hasAccount')}{' '}
            <Link to="/login" className="text-primary-300 hover:text-white font-bold hover:underline transition-colors">
                {t('auth.signInLink')}
            </Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;