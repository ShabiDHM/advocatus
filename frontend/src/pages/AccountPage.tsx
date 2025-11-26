// FILE: src/pages/AccountPage.tsx
// PHOENIX PROTOCOL - ACCOUNT PAGE FIX
// 1. TYPES: Corrected 'username' -> 'email'.
// 2. PASSWORD: Corrected 'old_password' -> 'current_password'.

import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { User, Lock, Trash2, Save, Loader2 } from 'lucide-react';

const AccountPage: React.FC = () => {
  const { user, logout } = useAuth();
  const { t } = useTranslation();
  
  const [passwords, setPasswords] = useState({ current: '', new: '', confirm: '' });
  const [isSaving, setIsSaving] = useState(false);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwords.new !== passwords.confirm) {
        alert(t('account.passwordMismatch', 'Fjalëkalimet nuk përputhen.'));
        return;
    }
    setIsSaving(true);
    try {
        await apiService.changePassword({
            current_password: passwords.current,
            new_password: passwords.new
        });
        alert(t('account.passwordUpdated', 'Fjalëkalimi u ndryshua me sukses.'));
        setPasswords({ current: '', new: '', confirm: '' });
    } catch (error) {
        console.error(error);
        alert(t('error.generic'));
    } finally {
        setIsSaving(false);
    }
  };

  const handleDeleteAccount = async () => {
      if (!window.confirm(t('account.confirmDelete', 'A jeni të sigurt? Ky veprim është i pakthyeshëm.'))) return;
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
        <h1 className="text-3xl font-bold text-text-primary mb-8">{t('account.title', 'Llogaria Ime')}</h1>
        
        <div className="grid gap-8">
            {/* Profile Info */}
            <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge">
                <h3 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                    <User className="text-primary-start" /> {t('account.profileInfo', 'Informacione Personale')}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm text-text-secondary mb-1">{t('auth.fullName', 'Emri i Plotë')}</label>
                        <div className="px-4 py-2 bg-background-dark rounded-lg text-white border border-glass-edge">
                            {user.full_name}
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-text-secondary mb-1">{t('auth.email', 'Email')}</label>
                        <div className="px-4 py-2 bg-background-dark rounded-lg text-white border border-glass-edge">
                            {user.email}
                        </div>
                    </div>
                    <div>
                        <label className="block text-sm text-text-secondary mb-1">{t('account.role', 'Roli')}</label>
                        <div className="px-4 py-2 bg-background-dark rounded-lg text-white border border-glass-edge capitalize">
                            {user.role.toLowerCase()}
                        </div>
                    </div>
                </div>
            </div>

            {/* Password Change */}
            <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge">
                <h3 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
                    <Lock className="text-secondary-start" /> {t('account.security', 'Siguria')}
                </h3>
                <form onSubmit={handlePasswordChange} className="space-y-4 max-w-md">
                    <input 
                        type="password" 
                        placeholder={t('account.currentPassword', 'Fjalëkalimi Aktual')}
                        required
                        value={passwords.current}
                        onChange={e => setPasswords({...passwords, current: e.target.value})}
                        className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-secondary-start outline-none"
                    />
                    <input 
                        type="password" 
                        placeholder={t('account.newPassword', 'Fjalëkalimi i Ri')}
                        required
                        value={passwords.new}
                        onChange={e => setPasswords({...passwords, new: e.target.value})}
                        className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-secondary-start outline-none"
                    />
                    <input 
                        type="password" 
                        placeholder={t('account.confirmPassword', 'Konfirmo Fjalëkalimin')}
                        required
                        value={passwords.confirm}
                        onChange={e => setPasswords({...passwords, confirm: e.target.value})}
                        className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-secondary-start outline-none"
                    />
                    <button type="submit" disabled={isSaving} className="px-6 py-2 rounded-lg bg-secondary-start hover:bg-secondary-end text-white font-medium transition-colors flex items-center gap-2 disabled:opacity-50">
                        {isSaving ? <Loader2 className="animate-spin w-4 h-4" /> : <Save className="w-4 h-4" />}
                        {t('general.save', 'Ruaj')}
                    </button>
                </form>
            </div>

            {/* Danger Zone */}
            <div className="bg-red-900/10 p-6 rounded-2xl border border-red-500/20">
                <h3 className="text-xl font-semibold text-red-400 mb-4 flex items-center gap-2">
                    <Trash2 /> {t('account.dangerZone', 'Zona e Rrezikut')}
                </h3>
                <p className="text-sm text-red-300/70 mb-4">{t('account.deleteWarning', 'Fshirja e llogarisë do të largojë të gjitha të dhënat tuaja përgjithmonë.')}</p>
                <button onClick={handleDeleteAccount} className="px-4 py-2 rounded-lg border border-red-500 text-red-400 hover:bg-red-500 hover:text-white transition-all">
                    {t('account.deleteAccount', 'Fshij Llogarinë')}
                </button>
            </div>
        </div>
    </div>
  );
};

export default AccountPage;