// FILE: src/pages/ResetPasswordPage.tsx
import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { KeyRound, CheckCircle, AlertTriangle, Eye, EyeOff } from 'lucide-react';
import { apiService } from '../services/api';
import BrandLogo from '../components/BrandLogo';

const ResetPasswordPage: React.FC = () => {
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const token = searchParams.get('token');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirm, setShowConfirm] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    useEffect(() => {
        if (!token) {
            setError('Link i pavlefshëm. Ju lutem kërkoni një link të ri.');
        }
    }, [token]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        if (password !== confirmPassword) {
            setError('Fjalëkalimet nuk përputhen.');
            return;
        }
        if (password.length < 8) {
            setError('Fjalëkalimi duhet të ketë të paktën 8 karaktere.');
            return;
        }
        setIsLoading(true);
        setError(null);
        try {
            await apiService.resetPassword(token, password);
            setSuccess(true);
            setTimeout(() => navigate('/login'), 3000);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Linku ka skaduar ose është i pavlefshëm.');
        } finally {
            setIsLoading(false);
        }
    };

    if (!token && !success) {
        return (
            <div className="min-h-screen bg-canvas flex items-center justify-center p-4">
                <div className="glass-panel max-w-md w-full p-8 rounded-2xl text-center">
                    <AlertTriangle size={48} className="mx-auto text-danger-start mb-4" />
                    <h2 className="text-xl font-bold text-text-primary mb-2">Link i pavlefshëm</h2>
                    <p className="text-text-secondary mb-6">{error}</p>
                    <Link to="/forgot-password" className="btn-primary inline-block px-6 py-2 rounded-lg">
                        Kërko një link të ri
                    </Link>
                </div>
            </div>
        );
    }

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
                <div className="glass-panel p-8 rounded-2xl border border-main">
                    {!success ? (
                        <>
                            <h2 className="text-2xl font-bold text-text-primary text-center mb-2">
                                {t('resetPassword.title', 'Vendosni fjalëkalimin e ri')}
                            </h2>
                            <p className="text-text-secondary text-center mb-8">
                                {t('resetPassword.subtitle', 'Zgjidhni një fjalëkalim të sigurt.')}
                            </p>
                            <form onSubmit={handleSubmit} className="space-y-6">
                                {error && (
                                    <div className="bg-danger-start/10 text-danger-start text-sm p-3 rounded-lg flex items-center gap-2 border border-danger-start/20">
                                        <AlertTriangle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                                        {t('resetPassword.password', 'Fjalëkalimi i ri')}
                                    </label>
                                    <div className="relative mt-2">
                                        <KeyRound size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type={showPassword ? 'text' : 'password'}
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-10 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start"
                                            placeholder="••••••••"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted"
                                        >
                                            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                        </button>
                                    </div>
                                </div>
                                <div>
                                    <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                                        {t('resetPassword.confirmPassword', 'Konfirmo fjalëkalimin')}
                                    </label>
                                    <div className="relative mt-2">
                                        <KeyRound size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type={showConfirm ? 'text' : 'password'}
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-10 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start"
                                            placeholder="••••••••"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowConfirm(!showConfirm)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted"
                                        >
                                            {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                                        </button>
                                    </div>
                                </div>
                                <button
                                    type="submit"
                                    disabled={isLoading}
                                    className="btn-primary w-full py-3 rounded-lg font-semibold disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {isLoading ? (
                                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                                    ) : (
                                        t('resetPassword.submit', 'Rivendos fjalëkalimin')
                                    )}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="text-center">
                            <CheckCircle size={48} className="mx-auto text-success-start mb-4" />
                            <h2 className="text-xl font-bold text-text-primary mb-2">
                                {t('resetPassword.successTitle', 'Fjalëkalimi u ndryshua!')}
                            </h2>
                            <p className="text-text-secondary">
                                {t('resetPassword.successMessage', 'Tani mund të hyni me fjalëkalimin tuaj të ri.')}
                            </p>
                            <p className="text-text-muted text-sm mt-4">Duke ju ridrejtuar te faqja e hyrjes...</p>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default ResetPasswordPage;