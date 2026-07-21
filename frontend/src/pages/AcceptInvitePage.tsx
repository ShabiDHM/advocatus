// FILE: src/pages/AcceptInvitePage.tsx
// PHOENIX PROTOCOL - ACCEPT INVITE V6.1 (FULL NAME ENHANCED)

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
            setError(t('invite.errorToken', 'Tokeni i ftesës mungon ose është i pavlefshëm.'));
        }
    }, [searchParams, t]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;

        if (username.trim().length < 3) {
            setError(t('invite.errorUsernameLength', 'Lutemi shkruani emrin dhe mbiemrin tuaj të plotë.'));
            return;
        }

        if (password.length < 8) {
            setError(t('invite.errorPassword', 'Fjalëkalimi duhet të ketë së paku 8 karaktere.'));
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const response = await apiService.acceptInvite({ token, username: username.trim(), password });
            setSuccess(response.message);
            setTimeout(() => navigate('/login'), 2500);
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || t('invite.errorGeneric', 'Aktivizimi dështoi. Lutemi provoni përsëri.');
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
                            <h2 className="text-2xl font-bold text-text-primary text-center mb-2">{t('invite.title', 'Prano Ftesën')}</h2>
                            <p className="text-text-secondary text-center mb-8">{t('invite.subtitle', 'Plotësoni të dhënat tuaja për të aktivizuar llogarinë.')}</p>

                            <form onSubmit={handleSubmit} className="space-y-6">
                                {error && (
                                    <div className="bg-danger-start/10 text-danger-start text-sm p-3 rounded-lg flex items-center gap-2 border border-danger-start/20">
                                        <AlertTriangle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}
                                
                                {/* Full Name / Username Input */}
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                                        {t('invite.fullNameLabel', 'Emri dhe Mbiemri i Plotë')}
                                    </label>
                                    <div className="relative mt-2">
                                        <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type="text"
                                            value={username}
                                            onChange={(e) => setUsername(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 text-sm text-text-primary placeholder:text-text-disabled"
                                            placeholder={t('invite.fullNamePlaceholder', 'Shkruani emrin dhe mbiemrin (shmb. Shaban Bala)')}
                                        />
                                    </div>
                                </div>

                                {/* Password Input */}
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                                        {t('invite.password', 'Fjalëkalimi i Ri')}
                                    </label>
                                    <div className="relative mt-2">
                                        <KeyRound size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 text-sm text-text-primary placeholder:text-text-disabled"
                                            placeholder={t('invite.passwordPlaceholder', 'Krijoni një fjalëkalim të sigurt (min 8 karaktere)')}
                                        />
                                    </div>
                                </div>

                                <button
                                    type="submit"
                                    disabled={isLoading || !token}
                                    className="btn-primary w-full py-3 rounded-lg font-semibold disabled:opacity-50 flex items-center justify-center gap-2 text-sm uppercase tracking-wider shadow-lg shadow-primary-start/15"
                                >
                                    {isLoading ? <Loader2 className="animate-spin" /> : t('invite.submitButton', 'Aktivizo Llogarinë')}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="text-center py-4">
                            <CheckCircle size={52} className="mx-auto text-success-start mb-4 animate-bounce" />
                            <h2 className="text-2xl font-bold text-text-primary mb-2">{t('invite.successTitle', 'Aktivizimi u Krye!')}</h2>
                            <p className="text-text-secondary mb-6 text-sm">{success}</p>
                            <p className="text-xs text-text-muted">{t('invite.redirecting', 'Po ju ridrejtojmë te faqja e kyçjes...')}</p>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default AcceptInvitePage;