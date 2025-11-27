// FILE: src/pages/RegisterPage.tsx
// PHOENIX PROTOCOL - CLEANED (No Unused Imports)

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { User, Mail, Lock, Loader2, CheckCircle, ShieldAlert } from 'lucide-react';

const RegisterPage: React.FC = () => {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const { t } = useTranslation();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await apiService.register({ email, password, full_name: fullName });
      setIsSuccess(true);
    } catch (err: any) {
      console.error("Registration Error:", err);
      let msg = t('auth.registerFailed', 'Regjistrimi dështoi.');
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

  if (isSuccess) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background-dark px-4">
        <div className="max-w-md w-full p-8 bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge shadow-2xl text-center">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-green-500/10">
                <CheckCircle className="w-10 h-10 text-green-400" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-4">{t('auth.registrationSuccess', 'Llogaria u Krijua!')}</h2>
            <p className="text-text-secondary mb-8 leading-relaxed">{t('auth.gatekeeperMessage', 'Llogaria juaj është krijuar...')}</p>
            
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-xl p-4 mb-8 flex items-start gap-3 text-left">
                <ShieldAlert className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                    <p className="text-sm font-semibold text-yellow-200 mb-1">{t('auth.securityNotice', 'Njoftim Sigurie')}</p>
                    <p className="text-xs text-yellow-200/80">{t('auth.approvalWait', 'Ju lutemi prisni njoftimin...')}</p>
                </div>
            </div>

            <Link to="/login" className="block w-full py-3 px-4 bg-white/10 hover:bg-white/20 border border-white/10 rounded-xl text-white font-semibold transition-all">
                {t('auth.backToLogin', 'Kthehu te Hyrja')}
            </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4">
      <div className="max-w-md w-full space-y-8 p-8 bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge shadow-2xl">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white">{t('auth.registerTitle', 'Krijoni Llogari')}</h2>
          <p className="mt-2 text-sm text-text-secondary">{t('auth.registerSubtitle', 'Bashkohuni me platformën...')}</p>
        </div>
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-text-secondary mb-1">{t('auth.fullName', 'Emri i Plotë')}</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><User className="h-5 w-5 text-text-secondary" /></div>
                <input type="text" required value={fullName} onChange={(e) => setFullName(e.target.value)} className="block w-full pl-10 px-3 py-2 bg-background-dark/50 border border-glass-edge rounded-xl text-white placeholder-gray-500 focus:ring-2 focus:ring-primary-start outline-none" placeholder="Emri Mbiemri" />
              </div>
            </div>
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
            {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : t('auth.registerButton', 'Regjistrohu')}
          </button>
        </form>
        <div className="text-center text-sm">
          <span className="text-text-secondary">{t('auth.hasAccount', 'Keni llogari?')} </span>
          <Link to="/login" className="font-medium text-primary-start hover:text-primary-end transition-colors">{t('auth.loginLink', 'Hyni këtu')}</Link>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;