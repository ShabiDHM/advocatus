// FILE: src/pages/AccountPage.tsx
// PHOENIX PROTOCOL - ACCOUNT PAGE V2.0 (GLASS STYLE)
// 1. VISUALS: Applied global 'glass-panel' and 'glass-input' classes.
// 2. UX: Enhanced read-only fields to look like glass cards.
// 3. SAFETY: stylized the "Danger Zone" with a red-tinted glass effect.

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
        alert(t('account.passwordMismatch'));
        return;
    }
    setIsSaving(true);
    try {
        await apiService.changePassword({
            current_password: passwords.current,
            new_password: passwords.new
        });
        alert(t('account.passwordUpdated'));
        setPasswords({ current: '', new: '', confirm: '' });
    } catch (error) {
        console.error(error);
        alert(t('error.generic'));
    } finally {
        setIsSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
      if (!window.confirm(t('account.confirmDelete'))) return;
      try {
          await apiService.deleteAccount();
          logout();
      } catch (error) {
          console.error(error);
          alert(t('error.generic'));
      }
  };

  if (!user) return null;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
            <h1 className="text-3xl font-bold text-white mb-2">{t('account.title')}</h1>
            <p className="text-gray-400 text-sm">{t('account.subtitle', 'Menaxhoni të dhënat dhe sigurinë e llogarisë tuaj')}</p>
        </div>
        
        <div className="grid gap-8">
            {/* Profile Info - Glass Panel */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                    <User className="text-primary-start" size={24} /> 
                    {t('account.profileInfo')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">{t('account.username')}</label>
                        <div className="w-full px-4 py-3 bg-white/5 border border-white/5 rounded-xl text-gray-300 font-medium">
                            {user.username}
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">{t('account.email')}</label>
                        <div className="w-full px-4 py-3 bg-white/5 border border-white/5 rounded-xl text-gray-300 font-medium">
                            {user.email}
                        </div>
                    </div>
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">{t('account.role')}</label>
                        <div className="w-full px-4 py-3 bg-white/5 border border-white/5 rounded-xl text-gray-300 font-medium flex items-center gap-2">
                            <Shield size={16} className="text-secondary-start" />
                            <span className="capitalize">{user.role.toLowerCase()}</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Password Change - Glass Panel */}
            <div className="glass-panel p-6 rounded-2xl">
                <h3 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                    <Lock className="text-secondary-start" size={24} /> 
                    {t('account.security')}
                </h3>
                <form onSubmit={handlePasswordChange} className="space-y-5 max-w-lg">
                    <div className="space-y-1.5">
                        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">{t('account.currentPassword')}</label>
                        <input 
                            type="password" 
                            required
                            value={passwords.current}
                            onChange={e => setPasswords({...passwords, current: e.target.value})}
                            className="glass-input w-full px-4 py-3 rounded-xl"
                        />
                    </div>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                        <div className="space-y-1.5">
                            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">{t('account.newPassword')}</label>
                            <input 
                                type="password" 
                                required
                                value={passwords.new}
                                onChange={e => setPasswords({...passwords, new: e.target.value})}
                                className="glass-input w-full px-4 py-3 rounded-xl"
                            />
                        </div>
                        <div className="space-y-1.5">
                            <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">{t('account.confirmPassword')}</label>
                            <input 
                                type="password" 
                                required
                                value={passwords.confirm}
                                onChange={e => setPasswords({...passwords, confirm: e.target.value})}
                                className="glass-input w-full px-4 py-3 rounded-xl"
                            />
                        </div>
                    </div>

                    <div className="pt-2">
                        <button type="submit" disabled={isSaving} className="px-6 py-3 rounded-xl bg-gradient-to-r from-secondary-start to-secondary-end hover:opacity-90 text-white font-bold shadow-lg shadow-secondary-start/20 transition-all active:scale-95 flex items-center gap-2 disabled:opacity-50">
                            {isSaving ? <Loader2 className="animate-spin w-4 h-4" /> : <Save className="w-4 h-4" />}
                            {t('general.save')}
                        </button>
                    </div>
                </form>
            </div>

            {/* Danger Zone - Red Glass Panel */}
            <div className="relative overflow-hidden p-6 rounded-2xl border border-red-500/20 bg-red-500/5 backdrop-blur-sm">
                <div className="absolute top-0 right-0 p-10 bg-red-500/10 blur-[60px] rounded-full pointer-events-none"></div>
                
                <h3 className="text-xl font-semibold text-red-400 mb-4 flex items-center gap-2 relative z-10">
                    <Trash2 size={24} /> {t('account.dangerZone')}
                </h3>
                <p className="text-sm text-red-200/60 mb-6 max-w-xl relative z-10 leading-relaxed">
                    {t('account.deleteWarning')}
                </p>
                <button onClick={handleDeleteAccount} className="px-5 py-2.5 rounded-xl border border-red-500/30 text-red-400 hover:bg-red-500 hover:text-white transition-all font-medium relative z-10 active:scale-95">
                    {t('account.deleteAccount')}
                </button>
            </div>
        </div>
    </div>
  );
};

export default AccountPage;