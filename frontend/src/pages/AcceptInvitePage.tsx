// FILE: src/pages/AcceptInvitePage.tsx
// PHOENIX PROTOCOL - ACCEPT INVITE V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, btn-primary, text-text-primary, text-text-secondary, border-main.
// 2. Consistent with LoginPage and RegisterPage.
// 3. Preserved all logic and i18n.

import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import BrandLogo from '../components/BrandLogo';
import { Loader2, User, KeyRound, CheckCircle, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';

const AcceptInvitePage: React.FC = () => {
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const [token, setToken] = useState<string | null>(null);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);

    useEffect(() => {
        const urlToken = searchParams.get('token');
        if (urlToken) {
            setToken(urlToken);
        } else {
            setError(t('invite.errorToken'));
        }
    }, [searchParams, t]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;

        if (password.length < 8) {
            setError(t('invite.errorPassword'));
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const response = await apiService.acceptInvite({ token, username, password });
            setSuccess(response.message);
            setTimeout(() => navigate('/login'), 3000);
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || t('invite.errorGeneric');
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-canvas flex flex-col justify-center items-center p-4">
            <div className="absolute top-8">
                <BrandLogo />
            </div>
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md"
            >
                <div className="glass-panel p-8 rounded-2xl shadow-2xl border border-main">
                    {!success ? (
                        <>
                            <h2 className="text-2xl font-bold text-text-primary text-center mb-2">{t('invite.title')}</h2>
                            <p className="text-text-secondary text-center mb-8">{t('invite.subtitle')}</p>

                            <form onSubmit={handleSubmit} className="space-y-6">
                                {error && (
                                    <div className="bg-danger-start/10 text-danger-start text-sm p-3 rounded-lg flex items-center gap-2 border border-danger-start/20">
                                        <AlertTriangle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">{t('invite.username')}</label>
                                    <div className="relative mt-2">
                                        <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type="text"
                                            value={username}
                                            onChange={(e) => setUsername(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40"
                                            placeholder={t('invite.usernamePlaceholder')}
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">{t('invite.password')}</label>
                                    <div className="relative mt-2">
                                        <KeyRound size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40"
                                            placeholder={t('invite.passwordPlaceholder')}
                                        />
                                    </div>
                                </div>
                                <button
                                    type="submit"
                                    disabled={isLoading || !token}
                                    className="btn-primary w-full py-3 rounded-lg font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {isLoading ? <Loader2 className="animate-spin" /> : t('invite.submitButton')}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="text-center">
                            <CheckCircle size={48} className="mx-auto text-success-start mb-4" />
                            <h2 className="text-2xl font-bold text-text-primary mb-2">{t('invite.successTitle')}</h2>
                            <p className="text-text-secondary mb-6">{t('invite.successMessage')}</p>
                            <p className="text-sm text-text-secondary/70">{t('invite.redirecting')}</p>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default AcceptInvitePage;