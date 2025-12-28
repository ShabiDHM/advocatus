// FILE: src/pages/LoginPage.tsx
// PHOENIX PROTOCOL - LOGIN PAGE V3.0 (GLASS STYLE)
// 1. VISUALS: Applied 'glass-high' for the form container and 'glass-input' for fields.
// 2. LAYOUT: Added ambient background glows for visual depth.
// 3. LOGIC: Preserved all authentication, error handling, and redirection logic.

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
      console.error("Login Error:", err);
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
    <div className="min-h-screen flex items-center justify-center bg-background-dark px-4 relative overflow-hidden font-sans selection:bg-primary-start/30">
      
      {/* Ambient Background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[500px] h-[500px] bg-primary-start/20 rounded-full blur-[100px] opacity-40 animate-pulse-slow"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-secondary-start/20 rounded-full blur-[100px] opacity-30 animate-pulse-slow delay-1000"></div>
      </div>

      <div className="glass-high max-w-md w-full space-y-8 p-8 rounded-3xl shadow-2xl relative z-10 animate-in fade-in zoom-in-95 duration-300 border border-white/10">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-white tracking-tight">{t('auth.loginTitle')}</h2>
          <p className="mt-2 text-sm text-text-secondary">{t('auth.loginSubtitle')}</p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                  {t('auth.usernameOrEmail')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <User className="h-5 w-5 text-gray-500" />
                </div>
                <input 
                    type="text" 
                    required 
                    value={identity} 
                    onChange={(e) => setIdentity(e.target.value)} 
                    className="glass-input block w-full pl-10 px-4 py-3 rounded-xl" 
                    placeholder={t('auth.usernameOrEmailPlaceholder')} 
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-400 uppercase tracking-wider mb-1.5">
                  {t('auth.password')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-gray-500" />
                </div>
                <input 
                    type="password" 
                    required 
                    value={password} 
                    onChange={(e) => setPassword(e.target.value)} 
                    className="glass-input block w-full pl-10 px-4 py-3 rounded-xl" 
                    placeholder="••••••••" 
                />
              </div>
            </div>
          </div>

          {error && (
            <div className="text-red-300 text-sm text-center bg-red-500/10 p-3 rounded-xl border border-red-500/20 font-medium">
                {error}
            </div>
          )}

          <button 
            type="submit" 
            disabled={isSubmitting} 
            className="w-full flex justify-center py-3 px-4 rounded-xl text-white bg-gradient-to-r from-primary-start to-primary-end font-bold shadow-lg shadow-primary-start/20 hover:opacity-90 disabled:opacity-50 transition-all active:scale-95"
          >
            {isSubmitting ? <Loader2 className="animate-spin h-5 w-5" /> : t('auth.loginButton')}
          </button>
        </form>
        
        <div className="text-center text-sm pt-2">
          <span className="text-text-secondary">{t('auth.noAccount')} </span>
          <Link to="/register" className="font-bold text-primary-start hover:text-primary-end transition-colors hover:underline">
            {t('auth.registerLink')}
          </Link>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;