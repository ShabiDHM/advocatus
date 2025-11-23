// FILE: /home/user/advocatus-frontend/src/pages/AccountPage.tsx
// PHOENIX PROTOCOL - CLEANUP
// 1. REMOVED: Unused 'Shield' import to fix TypeScript warning.
// 2. STATUS: Clean, warning-free code.

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ChangePasswordRequest, AdminUser } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { AlertTriangle, User, Key } from 'lucide-react';

const ChangePasswordForm: React.FC = () => {
  const { t } = useTranslation();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    if (newPassword.length < 8) { setError(t('accountPage.passwordTooShort')); return; }
    if (newPassword !== confirmPassword) { setError(t('accountPage.passwordMismatch')); return; }
    setIsSubmitting(true);
    try {
      const data: ChangePasswordRequest = { old_password: oldPassword, new_password: newPassword };
      await apiService.changePassword(data);
      setSuccess(t('accountPage.passwordSuccess'));
      setOldPassword(''); setNewPassword(''); setConfirmPassword('');
    } catch (err: any) {
      setError(err.response?.data?.detail || t('accountPage.passwordFailure'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-6 rounded-2xl shadow-xl h-full flex flex-col">
      <div className="flex items-center gap-3 border-b border-glass-edge/50 pb-4 mb-6">
        <div className="p-2 bg-primary-start/20 rounded-lg">
            <Key className="w-5 h-5 text-primary-start" />
        </div>
        <h3 className="text-xl font-bold text-text-primary">{t('accountPage.securityTitle')}</h3>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-5 flex-grow">
        {success && <div className="p-3 text-sm text-green-100 bg-green-500/20 border border-green-500/50 rounded-xl">{success}</div>}
        {error && <div className="p-3 text-sm text-red-100 bg-red-500/20 border border-red-500/50 rounded-xl">{error}</div>}
        
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">{t('accountPage.oldPassword')}</label>
          <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required className="w-full px-4 py-3 bg-background-dark/50 rounded-xl text-text-primary focus:ring-2 focus:ring-primary-start border border-glass-edge transition-all outline-none" disabled={isSubmitting} />
        </div>
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">{t('accountPage.newPassword')}</label>
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required className="w-full px-4 py-3 bg-background-dark/50 rounded-xl text-text-primary focus:ring-2 focus:ring-primary-start border border-glass-edge transition-all outline-none" disabled={isSubmitting} />
        </div>
        <div>
          <label className="block text-sm font-medium text-text-secondary mb-1">{t('accountPage.confirmPassword')}</label>
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className="w-full px-4 py-3 bg-background-dark/50 rounded-xl text-text-primary focus:ring-2 focus:ring-primary-start border border-glass-edge transition-all outline-none" disabled={isSubmitting} />
        </div>
        
        <div className="pt-2">
            <motion.button 
                type="submit" 
                className="w-full text-white font-semibold py-3 px-6 rounded-xl transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end disabled:opacity-50" 
                disabled={isSubmitting} 
                whileHover={{ scale: 1.02 }} 
                whileTap={{ scale: 0.98 }}
            >
                {isSubmitting ? t('accountPage.saving') : t('accountPage.changePasswordButton')}
            </motion.button>
        </div>
      </form>
    </div>
  );
};

const DeleteAccountPanel: React.FC = () => {
    const { t } = useTranslation();
    const { logout } = useAuth();
    const [isDeleting, setIsDeleting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleDelete = async () => {
        if (window.prompt(t('accountPage.deleteAccount.prompt')) !== t('accountPage.deleteAccount.confirmText')) {
            return;
        }
        setIsDeleting(true);
        setError(null);
        try {
            await apiService.deleteAccount();
            alert(t('accountPage.deleteAccount.successMessage'));
            logout();
        } catch (err: any) {
            setError(err.response?.data?.detail || t('accountPage.deleteAccount.failureMessage'));
            setIsDeleting(false);
        }
    };

    return (
        <div className="bg-red-500/5 border border-red-500/30 p-6 rounded-2xl shadow-lg mt-8">
            <div className="flex items-start sm:items-center gap-4 flex-col sm:flex-row justify-between">
                <div className="space-y-1">
                    <h3 className="text-lg font-bold text-red-400 flex items-center gap-2">
                        <AlertTriangle className="h-5 w-5" /> {t('accountPage.deleteAccount.title')}
                    </h3>
                    <p className="text-sm text-text-secondary max-w-2xl">{t('accountPage.deleteAccount.warning')}</p>
                </div>
                
                <div className="w-full sm:w-auto mt-4 sm:mt-0">
                    <motion.button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="w-full sm:w-auto text-white font-bold py-2.5 px-6 rounded-xl shadow-md bg-red-600 hover:bg-red-700 disabled:opacity-50 transition-colors"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        {isDeleting ? t('accountPage.deleteAccount.deleting') : t('accountPage.deleteAccount.buttonText')}
                    </motion.button>
                </div>
            </div>
            {error && <div className="mt-4 p-3 text-sm text-red-100 bg-red-500/20 border border-red-500/50 rounded-lg">{error}</div>}
        </div>
    );
};

const AccountPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [userDetails, setUserDetails] = useState<AdminUser | null>(null); 
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUserDetails = async () => {
        if (!user) return;
        setIsLoading(true);
        try {
            const data = await apiService.fetchUserProfile() as AdminUser; 
            setUserDetails(data);
        } catch (err) {
            setError(t('accountPage.fetchFailure'));
        } finally {
            setIsLoading(false);
        }
    };
    fetchUserDetails();
  }, [user, t]);

  if (isLoading) { return <div className="text-text-secondary text-center py-20">{t('accountPage.loading')}</div>; }
  if (error || !userDetails) { return <div className="text-red-500 text-center py-20">{error || t('accountPage.noUserFound')}</div>; }

  return (
    <motion.div 
        className="account-page max-w-6xl mx-auto px-4 sm:px-6 py-8" 
        initial={{ opacity: 0, y: 10 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ duration: 0.3 }}
    >
      <div className="mb-8 border-b border-glass-edge/30 pb-4">
        <h1 className="text-3xl font-extrabold text-text-primary">{t('accountPage.pageTitle')}</h1>
        <p className="text-text-secondary mt-1 text-sm">{t('accountPage.subTitle') || "Manage your profile and security settings"}</p>
      </div>
      
      {/* 2-Column Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Profile Info (Takes 1/3 width on large screens) */}
        <div className="lg:col-span-1">
            <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-6 rounded-2xl shadow-xl h-full">
                <div className="flex items-center gap-3 border-b border-glass-edge/50 pb-4 mb-6">
                    <div className="p-2 bg-blue-500/20 rounded-lg">
                        <User className="w-5 h-5 text-blue-400" />
                    </div>
                    <h2 className="text-xl font-bold text-text-primary">{t('accountPage.profileTitle')}</h2>
                </div>
                
                <div className="space-y-6">
                    <div className="flex items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-2xl font-bold text-white shadow-lg">
                            {userDetails.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <p className="text-sm text-text-secondary">{t('accountPage.role')}</p>
                            <p className="text-lg font-semibold text-text-primary capitalize bg-blue-500/10 px-2 py-0.5 rounded text-blue-300 inline-block mt-1">
                                {userDetails.role}
                            </p>
                        </div>
                    </div>

                    <div className="space-y-4 pt-4 border-t border-glass-edge/30">
                        <div>
                            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{t('auth.username')}</label>
                            <p className="text-base text-text-primary font-medium mt-1">{userDetails.username}</p>
                        </div>
                        <div>
                            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider">{t('auth.email')}</label>
                            <p className="text-base text-text-primary font-medium mt-1 break-all">{userDetails.email}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        {/* Right Column: Change Password (Takes 2/3 width on large screens) */}
        <div className="lg:col-span-2">
            <ChangePasswordForm />
        </div>
      </div>

      {/* Bottom Row: Danger Zone */}
      <DeleteAccountPanel />
    </motion.div>
  );
};

export default AccountPage;