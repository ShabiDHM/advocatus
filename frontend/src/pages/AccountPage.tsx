// FILE: /home/user/advocatus-frontend/src/pages/AccountPage.tsx
// PHOENIX PROTOCOL - MOBILE OPTIMIZATION
// 1. RESPONSIVE PADDING: Changed all 'p-6' to 'p-4 sm:p-6' to gain screen width on mobile.
// 2. TOUCH TARGETS: Made buttons full-width (w-full) on mobile for easier tapping.
// 3. LAYOUT: Stacked form actions vertically on mobile, side-by-side on desktop.

import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { ChangePasswordRequest, AdminUser, ApiKey, ApiKeyCreateRequest } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'framer-motion';
import { KeyRound, Trash2, PlusCircle, AlertTriangle } from 'lucide-react';

const ApiKeyManager: React.FC = () => {
    const { t } = useTranslation();
    const [keys, setKeys] = useState<ApiKey[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [provider, setProvider] = useState<'openai' | 'anthropic'>('openai');
    const [keyName, setKeyName] = useState('');
    const [apiKey, setApiKey] = useState('');
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const fetchKeys = async () => {
        setIsLoading(true);
        try {
            const userKeys = await apiService.getUserApiKeys();
            setKeys(userKeys);
        } catch (err) {
            setError(t('accountPage.apiKey.fetchFailed'));
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchKeys();
    }, [t]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setSuccess(null);
        if (!keyName || !apiKey) {
            setError(t('accountPage.apiKey.fieldsRequired'));
            return;
        }
        setIsSubmitting(true);
        try {
            const data: ApiKeyCreateRequest = { provider, key_name: keyName, api_key: apiKey };
            await apiService.addApiKey(data);
            setSuccess(t('accountPage.apiKey.addSuccess'));
            setKeyName('');
            setApiKey('');
            await fetchKeys();
        } catch (err: any) {
            setError(err.response?.data?.detail || t('accountPage.apiKey.addFailed'));
        } finally {
            setIsSubmitting(false);
        }
    };
    
    const handleDelete = async (keyId: string) => {
        if (!window.confirm(t('accountPage.apiKey.confirmDelete'))) return;
        try {
            await apiService.deleteApiKey(keyId);
            setSuccess(t('accountPage.apiKey.deleteSuccess'));
            setKeys(keys.filter(k => k.id !== keyId));
        } catch (err: any) {
            setError(err.response?.data?.detail || t('accountPage.apiKey.deleteFailed'));
        }
    };

    return (
        <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-4 sm:p-6 rounded-2xl shadow-xl space-y-4">
            <h3 className="text-xl font-bold text-text-primary border-b border-glass-edge/50 pb-2 flex items-center">
                <KeyRound className="mr-3 h-6 w-6 text-primary-start" /> {t('accountPage.apiKey.title')}
            </h3>
            <p className="text-sm text-text-secondary">{t('accountPage.apiKey.description')}</p>
            
            <form onSubmit={handleSubmit} className="space-y-3 p-4 bg-background-dark/30 rounded-xl border border-glass-edge/50">
                {success && <div className="p-2 text-sm text-green-100 bg-success-start/70 rounded-lg">{success}</div>}
                {error && <div className="p-2 text-sm text-red-100 bg-red-700 rounded-lg">{error}</div>}
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input 
                        type="text" 
                        placeholder={t('accountPage.apiKey.keyName')} 
                        value={keyName} 
                        onChange={e => setKeyName(e.target.value)} 
                        className="w-full px-3 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" 
                    />
                    <input 
                        type="password" 
                        placeholder={t('accountPage.apiKey.apiKey')} 
                        value={apiKey} 
                        onChange={e => setApiKey(e.target.value)} 
                        className="w-full md:col-span-2 px-3 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge" 
                    />
                </div>
                
                {/* PHOENIX FIX: Stack controls on mobile, row on desktop */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                    <select 
                        value={provider} 
                        onChange={e => setProvider(e.target.value as any)} 
                        className="w-full sm:w-auto px-3 py-2 bg-background-dark/50 rounded-xl text-text-primary focus:ring-primary-start focus:border-primary-start border border-glass-edge appearance-none"
                    >
                        <option value="openai">OpenAI</option>
                        <option value="anthropic">Anthropic</option>
                    </select>
                    
                    <motion.button 
                        type="submit" 
                        disabled={isSubmitting} 
                        className="w-full sm:w-auto flex items-center justify-center text-white font-semibold py-2 px-4 rounded-xl shadow-lg bg-gradient-to-r from-primary-start to-primary-end disabled:opacity-50" 
                        whileHover={{ scale: 1.02 }} 
                        whileTap={{ scale: 0.98 }}
                    >
                        <PlusCircle className="mr-2 h-5 w-5" /> {isSubmitting ? t('accountPage.saving') : t('accountPage.apiKey.addButton')}
                    </motion.button>
                </div>
            </form>

            <div className="space-y-2">
                <AnimatePresence>
                    {keys.map(key => (
                        <motion.div 
                            key={key.id} 
                            layout 
                            initial={{ opacity: 0 }} 
                            animate={{ opacity: 1 }} 
                            exit={{ opacity: 0 }} 
                            className="flex items-center justify-between p-3 bg-background-dark/30 rounded-xl border border-glass-edge/50"
                        >
                            <div className="min-w-0 pr-2">
                                <p className="font-semibold text-text-primary truncate">
                                    {key.key_name} 
                                    <span className="text-xs font-mono text-primary-start ml-2 hidden sm:inline">({key.provider})</span>
                                </p>
                                {/* Mobile-only provider badge */}
                                <span className="text-xs font-mono text-primary-start sm:hidden block mb-1">{key.provider}</span>
                                <p className="text-xs text-text-secondary">{t('accountPage.apiKey.usage')}: {key.usage_count}</p>
                            </div>
                            <motion.button 
                                onClick={() => handleDelete(key.id)} 
                                className="text-red-500 hover:text-red-400 flex-shrink-0 p-2" 
                                whileHover={{ scale: 1.1 }}
                            >
                                <Trash2 className="h-5 w-5" />
                            </motion.button>
                        </motion.div>
                    ))}
                </AnimatePresence>
                {isLoading && <p className="text-text-secondary text-sm">{t('accountPage.apiKey.loadingKeys')}</p>}
            </div>
        </div>
    );
};

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
    <motion.div className="account-page space-y-6 sm:space-y-8 max-w-5xl mx-auto" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
      <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary border-b border-glass-edge/50 pb-4 px-2 sm:px-0">{t('accountPage.pageTitle')}</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 items-start">
        <div className="space-y-6 sm:space-y-8">
            <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge p-4 sm:p-6 rounded-2xl shadow-xl space-y-4">
              <h2 className="text-xl font-bold text-text-primary border-b border-glass-edge/50 pb-2">{t('accountPage.profileTitle')}</h2>
              <div className="space-y-3 text-text-secondary text-sm sm:text-base">
                <p className="flex flex-col sm:flex-row sm:gap-2"><span className="font-medium text-text-primary">{t('auth.username')}:</span> {userDetails.username}</p>
                <p className="flex flex-col sm:flex-row sm:gap-2"><span className="font-medium text-text-primary">{t('auth.email')}:</span> <span className="break-all">{userDetails.email}</span></p>
                <p className="flex flex-col sm:flex-row sm:gap-2"><span className="font-medium text-text-primary">{t('accountPage.role')}:</span> {userDetails.role}</p>
              </div>
            </div>
            <ChangePasswordForm />
        </div>
        <ApiKeyManager />
      </div>

      <div className="mt-8 pt-8 border-t border-red-500/30">
        <DeleteAccountPanel />
      </div>
    </motion.div>
  );
};

export default AccountPage;