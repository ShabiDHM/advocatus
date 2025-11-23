// FILE: /home/user/advocatus-frontend/src/pages/AccountPage.tsx
// PHOENIX PROTOCOL - CLEANED VERSION
// 1. REMOVED: ApiKeyManager component and all related logic.
// 2. LAYOUT: Switched to a centered single-column layout (max-w-3xl) for better aesthetics.
// 3. CLEANUP: Removed unused imports and icons.

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ChangePasswordRequest, AdminUser } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';

// --- REMOVED ApiKeyManager Component ---

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
    <form onSubmit={handleSubmit} className="space-y-4 bg-background-light/50 backdrop-blur-md border border-glass-edge p-4 sm:p-6 rounded-2xl shadow-xl">
      <h3 className="text-xl font-bold text-text-primary border-b border-glass-edge/50 pb-2">{t('accountPage.securityTitle')}</h3>
      {success && <div className="p-3 text-sm text-green-100 bg-success-start/70 rounded-xl">{success}</div>}
      {error && <div className="p-3 text-sm text-red-100 bg-red-700 rounded-xl">{error}</div>}
      <div>
        <label className="block text-sm font-medium text-text-secondary">{t('accountPage.oldPassword')}</label>
        <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required className="w-full mt-1 px-3 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" disabled={isSubmitting} />
      </div>
      <div>
        <label className="block text-sm font-medium text-text-secondary">{t('accountPage.newPassword')}</label>
        <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required className="w-full mt-1 px-3 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" disabled={isSubmitting} />
      </div>
      <div>
        <label className="block text-sm font-medium text-text-secondary">{t('accountPage.confirmPassword')}</label>
        <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required className="w-full mt-1 px-3 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" disabled={isSubmitting} />
      </div>
      <motion.button 
        type="submit" 
        className="w-full sm:w-auto flex justify-center text-white font-semibold py-2 px-6 rounded-xl transition-all duration-300 shadow-lg glow-primary bg-gradient-to-r from-primary-start to-primary-end disabled:opacity-50" 
        disabled={isSubmitting} 
        whileHover={{ scale: 1.02 }} 
        whileTap={{ scale: 0.98 }}
      >
        {isSubmitting ? t('accountPage.saving') : t('accountPage.changePasswordButton')}
      </motion.button>
    </form>
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
        <div className="bg-red-900/30 border border-red-500/50 p-4 sm:p-6 rounded-2xl shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-red-300 flex items-center">
                <AlertTriangle className="mr-3 h-6 w-6" /> {t('accountPage.deleteAccount.title')}
            </h3>
            <p className="text-sm text-red-300/80">{t('accountPage.deleteAccount.warning')}</p>
            {error && <div className="p-2 text-sm text-red-100 bg-red-700 rounded-lg">{error}</div>}
            <motion.button
                onClick={handleDelete}
                disabled={isDeleting}
                className="w-full text-white font-bold py-3 px-4 rounded-xl shadow-lg bg-red-600 hover:bg-red-700 disabled:opacity-50"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
            >
                {isDeleting ? t('accountPage.deleteAccount.deleting') : t('accountPage.deleteAccount.buttonText')}
            </motion.button>
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

  if (isLoading) { return <div className="text-text-secondary text-center py-10">{t('accountPage.loading')}</div>; }
  if (error || !userDetails) { return <div className="text-red-500 text-center py-10">{error || t('accountPage.noUserFound')}</div>; }

  return (
    <motion.div 
        className="account-page space-y-6 sm:space-y-8 max-w-3xl mx-auto" 
        initial={{ opacity: 0, y: 10 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ duration: 0.3 }}
    >
      <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary border-b border-glass-edge/50 pb-4 px-2 sm:px-0 text-center sm:text-left">
          {t('accountPage.pageTitle')}
      </h1>
      
      {/* Layout: Single Column Stack */}
      <div className="space-y-6 sm:space-y-8">
        
        {/* Profile Info Section */}
        <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-4 sm:p-6 rounded-2xl shadow-xl space-y-4">
            <h2 className="text-xl font-bold text-text-primary border-b border-glass-edge/50 pb-2">{t('accountPage.profileTitle')}</h2>
            <div className="space-y-3 text-text-secondary text-sm sm:text-base">
            <p className="flex flex-col sm:flex-row sm:gap-2"><span className="font-medium text-text-primary">{t('auth.username')}:</span> {userDetails.username}</p>
            <p className="flex flex-col sm:flex-row sm:gap-2"><span className="font-medium text-text-primary">{t('auth.email')}:</span> <span className="break-all">{userDetails.email}</span></p>
            <p className="flex flex-col sm:flex-row sm:gap-2"><span className="font-medium text-text-primary">{t('accountPage.role')}:</span> {userDetails.role}</p>
            </div>
        </div>

        {/* Change Password Section */}
        <ChangePasswordForm />
      </div>

      <div className="mt-8 pt-8 border-t border-red-500/30">
        <DeleteAccountPanel />
      </div>
    </motion.div>
  );
};

export default AccountPage;