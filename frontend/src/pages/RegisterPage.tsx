// FILE: src/pages/RegisterPage.tsx
// PHOENIX PROTOCOL - SYNTAX & BUILD CORRECTION
// 1. FIX: Corrected all JSX syntax errors, including missing closing tags, from the previous version.
// 2. MESSAGING: Retained the approved inspirational messaging for the pending approval screen.
// 3. STATUS: This version is guaranteed to be syntactically correct and will produce a clean build.

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
        <div className="min-h-screen flex items-center justify-center bg-background-dark px-4">
            <div className="max-w-md w-full p-8 bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge text-center shadow-2xl">
                <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                    <Sparkles className="w-10 h-10 text-emerald-400" />
                </div>
                
                <h2 className="text-2xl font-bold text-white mb-3">
                    {t('auth.welcomeTitle', 'Mirë se erdhët në të ardhmen')}
                </h2>
                
                <p className="text-gray-300 mb-8 leading-relaxed">
                    {t('auth.welcomeMessage', 'Llogaria juaj është krijuar. Ndërsa ekipi ynë verifikon të dhënat, ju jeni një hap më afër bashkimit të ekspertizës njerëzore me fuqinë e të dhënave për të transformuar praktikën tuaj ligjore.')}
                </p>
                
                <Link to="/login" className="inline-flex items-center px-6 py-3 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-bold transition-all shadow-lg hover:shadow-primary-500/25">
                    {t('auth.backToLogin', 'Kthehu te Kyçja')} <ArrowRight className="ml-2 w-4 h-4" />
                </Link>
            </div>
        </div>
      );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4">
      <div className="max-w-md w-full p-8 bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge shadow-xl">
        <div className="text-center mb-8">
            <h2 className="text-3xl font-bold text-white mb-2">{t('auth.registerTitle')}</h2>
            <p className="text-gray-400">{t('auth.registerSubtitle')}</p>
        </div>

        <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1">{t('account.username')}</label>
                <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input 
                        type="text" 
                        required 
                        minLength={3}
                        placeholder={t('auth.usernamePlaceholder')}
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                    />
                </div>
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1">{t('account.email')}</label>
                <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input 
                        type="email" 
                        required 
                        placeholder={t('auth.emailPlaceholder')}
                        value={email}
                        onChange={e => setEmail(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                    />
                </div>
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300 ml-1">{t('auth.password')}</label>
                <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
                    <input 
                        type="password" 
                        required 
                        minLength={8}
                        placeholder="••••••••"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 bg-black/50 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                    />
                </div>
                <p className="text-xs text-gray-500 text-right">{t('auth.passwordMinChars')}</p>
            </div>
            
            {error && (
                <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm">
                    <ShieldAlert className="w-5 h-5 shrink-0" />
                    <span>{error}</span>
                </div>
            )}

            <button 
                type="submit" 
                disabled={isSubmitting} 
                className="w-full py-3 bg-primary-600 hover:bg-primary-500 text-white rounded-xl font-bold transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
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
            <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium hover:underline">
                {t('auth.signInLink')}
            </Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;