// FILE: src/pages/ForgotPasswordPage.tsx
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Mail, ArrowLeft, CheckCircle, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';
import BrandLogo from '../components/BrandLogo';

const ForgotPasswordPage: React.FC = () => {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const [email, setEmail] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);
        try {
            await apiService.forgotPassword(email);
            setSuccess(true);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Ndodhi një gabim. Provoni përsëri.');
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
                <div className="glass-panel p-8 rounded-2xl border border-main">
                    {!success ? (
                        <>
                            <h2 className="text-2xl font-bold text-text-primary text-center mb-2">
                                {t('forgotPassword.title', 'Harruat fjalëkalimin?')}
                            </h2>
                            <p className="text-text-secondary text-center mb-8">
                                {t('forgotPassword.subtitle', 'Shkruani email-in tuaj dhe ne do t\'ju dërgojmë një link për rivendosje.')}
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
                                        {t('forgotPassword.email', 'Email')}
                                    </label>
                                    <div className="relative mt-2">
                                        <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                                        <input
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg border border-main bg-surface focus:border-primary-start"
                                            placeholder="ju@example.com"
                                        />
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
                                        t('forgotPassword.submit', 'Dërgo linkun')
                                    )}
                                </button>
                                <div className="text-center">
                                    <Link to="/login" className="text-sm text-primary-start hover:underline inline-flex items-center gap-1">
                                        <ArrowLeft size={14} /> {t('forgotPassword.backToLogin', 'Kthehu te hyrja')}
                                    </Link>
                                </div>
                            </form>
                        </>
                    ) : (
                        <div className="text-center">
                            <CheckCircle size={48} className="mx-auto text-success-start mb-4" />
                            <h2 className="text-xl font-bold text-text-primary mb-2">
                                {t('forgotPassword.successTitle', 'Linku u dërgua!')}
                            </h2>
                            <p className="text-text-secondary">
                                {t('forgotPassword.successMessage', 'Nëse ekziston një llogari me këtë email, do të merrni një link për rivendosje.')}
                            </p>
                            <button
                                onClick={() => navigate('/login')}
                                className="mt-6 btn-secondary px-6 py-2 rounded-lg"
                            >
                                {t('forgotPassword.goToLogin', 'Shko te hyrja')}
                            </button>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default ForgotPasswordPage;