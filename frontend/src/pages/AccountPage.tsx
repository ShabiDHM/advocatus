// FILE: src/pages/AccountPage.tsx
// PHOENIX PROTOCOL - ACCOUNT PAGE V7.0 (VIBRANT DANGER ZONE & EXECUTIVE DESIGN)

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { User, Lock, Trash2, Save, Loader2, Shield } from 'lucide-react';

const AccountPage: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });
  const [isSaving, setIsSaving] = useState(false);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) {
        alert(t('account.passwordMismatch', 'Fjalëkalimet e reja nuk përputhen.'));
        return;
    }
    setIsSaving(true);
    try {
        await apiService.changePassword({
            current_password: passwords.current,
            new_password: passwords.new
        });
        alert(t('account.passwordUpdated', 'Fjalëkalimi u përditësua me sukses.'));
        setPasswords({ current: '', new: '', confirm: '' });
    } catch (error) {
        console.error(error);
        alert(t('error.generic', 'Ndodhi një gabim. Ju lutem provoni përsëri.'));
    } finally {
        setIsSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
      if (!window.confirm(t('account.confirmDelete', 'A jeni të sigurt se dëshironi të fshini llogarinë tuaj? Ky veprim nuk mund të kthehet.'))) return;
      try {
          await apiService.deleteAccount();
          logout();
      } catch (error) {
          console.error(error);
          alert(t('error.generic', 'Ndodhi një gabim gjatë fshirjes së llogarisë.'));
      }
  };

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 pb-16 bg-canvas text-text-primary">
        <div className="mb-8">
            <h1 className="text-3xl font-black text-text-primary mb-2 uppercase tracking-tight">{t('account.title', 'Llogaria Juaj')}</h1>
            <p className="text-text-secondary text-sm font-medium">{t('account.subtitle', 'Menaxhoni të dhënat dhe sigurinë e llogarisë tuaj')}</p>
        </div>
        
        <div className="grid gap-8">
            {/* Profile Info - Glass Panel */}
            <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-main bg-surface shadow-sm">
                <h3 className="text-xl font-bold text-text-primary mb-6 flex items-center gap-3">
                    <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20">
                        <User size={20} />
                    </div>
                    {t('account.profileInfo', 'Informatat e Profilit')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold uppercase tracking-wider text-text-muted ml-1">{t('account.username', 'Përdoruesi')}</label>
                        <div className="w-full px-4 py-3 bg-canvas border border-main rounded-xl text-text-primary font-bold">
                            {user.username}
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold uppercase tracking-wider text-text-muted ml-1">{t('account.email', 'Email')}</label>
                        <div className="w-full px-4 py-3 bg-canvas border border-main rounded-xl text-text-primary font-bold">
                            {user.email}
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold uppercase tracking-wider text-text-muted ml-1">{t('account.role', 'Roli')}</label>
                        <div className="w-full px-4 py-3 bg-canvas border border-main rounded-xl text-text-primary font-bold flex items-center gap-2">
                            <Shield size={16} className="text-primary-start" />
                            <span className="capitalize">{user.role.toLowerCase()}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Password Change - Security Panel */}
            <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-main bg-surface shadow-sm">
                <h3 className="text-xl font-bold text-text-primary mb-6 flex items-center gap-3">
                    <div className="p-2.5 bg-primary-start/10 text-primary-start rounded-xl border border-primary-start/20">
                        <Lock size={20} /> 
                    </div>
                    {t('account.security', 'Siguria dhe Fjalëkalimi')}
                </h3>
                <form onSubmit={handlePasswordChange} className="space-y-5 max-w-lg">
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold uppercase tracking-wider text-text-muted ml-1">{t('account.currentPassword', 'Fjalëkalimi Aktual')}</label>
                        <input 
                            type="password" 
                            required
                            value={passwords.current}
                            onChange={e => setPasswords({...passwords, current: e.target.value})}
                            className="w-full px-4 py-3 rounded-xl border border-main bg-canvas text-text-primary font-medium focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 outline-none transition-all"
                        />
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                        <div className="space-y-1.5">
                            <label className="block text-xs font-bold uppercase tracking-wider text-text-muted ml-1">{t('account.newPassword', 'Fjalëkalimi i Ri')}</label>
                            <input 
                                type="password" 
                                required
                                value={passwords.new}
                                onChange={e => setPasswords({...passwords, new: e.target.value})}
                                className="w-full px-4 py-3 rounded-xl border border-main bg-canvas text-text-primary font-medium focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 outline-none transition-all"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="block text-xs font-bold uppercase tracking-wider text-text-muted ml-1">{t('account.confirmPassword', 'Konfirmo Fjalëkalimin')}</label>
                            <input 
                                type="password" 
                                required
                                value={passwords.confirm}
                                onChange={e => setPasswords({...passwords, confirm: e.target.value})}
                                className="w-full px-4 py-3 rounded-xl border border-main bg-canvas text-text-primary font-medium focus:border-primary-start focus:ring-2 focus:ring-primary-start/20 outline-none transition-all"
                            />
                        </div>
                    </div>

                    <div className="pt-2">
                        <button type="submit" disabled={isSaving} className="btn-primary px-6 py-3 rounded-xl font-bold shadow-md transition-all active:scale-[0.98] flex items-center gap-2 disabled:opacity-50 cursor-pointer">
                            {isSaving ? <Loader2 className="animate-spin w-4 h-4" /> : <Save className="w-4 h-4" />}
                            {t('general.save', 'Ruaj Ndryshimet')}
                        </button>
                    </div>
                </form>
            </div>

            {/* Danger Zone - Red Glass Panel */}
            <div className="relative overflow-hidden p-6 sm:p-8 rounded-3xl border-2 border-rose-500/40 bg-rose-500/10 dark:bg-rose-950/20 backdrop-blur-md shadow-md">
                <div className="absolute -top-12 -right-12 w-48 h-48 bg-rose-500/20 blur-3xl rounded-full pointer-events-none"></div>
                
                <div className="flex items-center gap-3 mb-3 relative z-10">
                    <div className="p-2.5 bg-rose-500/20 text-rose-500 rounded-xl border border-rose-500/30 shrink-0">
                        <Trash2 size={22} />
                    </div>
                    <h3 className="text-xl font-black text-rose-600 dark:text-rose-400 uppercase tracking-tight">
                        {t('account.dangerZone', 'Zona e Rrezikut')}
                    </h3>
                </div>

                <p className="text-sm font-medium text-rose-700/90 dark:text-rose-300/90 mb-6 max-w-xl relative z-10 leading-relaxed">
                    {t('account.deleteWarning', 'Fshirja e llogarisë është e përhershme. Të gjitha të dhënat e llogarisë dhe rasteve tuaja do të fshihen në mënyrë të pakthyeshme.')}
                </p>

                <button 
                    type="button"
                    onClick={handleDeleteAccount} 
                    className="px-6 py-3 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs uppercase tracking-wider shadow-md hover:shadow-rose-500/20 transition-all relative z-10 active:scale-95 cursor-pointer flex items-center gap-2"
                >
                    <Trash2 size={16} />
                    {t('account.deleteAccount', 'Fshij Llogarinë')}
                </button>
            </div>
        </div>
    </div>
  );
};

export default AccountPage;