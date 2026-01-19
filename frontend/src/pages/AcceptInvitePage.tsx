// FILE: src/pages/AcceptInvitePage.tsx
// PHOENIX PROTOCOL - INVITATION ACCEPTANCE V1.1 (PATH FIX)
// 1. FIX: Corrected import path for BrandLogo component.
// 2. CLEANUP: Removed unused 'Link' import.

import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import BrandLogo from '../components/BrandLogo'; // Corrected Path
import { Loader2, User, KeyRound, CheckCircle, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';

const AcceptInvitePage: React.FC = () => {
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
            setError("Invitation token is missing or invalid.");
        }
    }, [searchParams]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;

        if (password.length < 8) {
            setError("Password must be at least 8 characters long.");
            return;
        }

        setIsLoading(true);
        setError(null);

        try {
            const response = await apiService.acceptInvite({ token, username, password });
            setSuccess(response.message);
            setTimeout(() => navigate('/login'), 3000);
        } catch (err: any) {
            const errorMessage = err.response?.data?.detail || "Failed to activate account. The token may be invalid or expired.";
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background-dark flex flex-col justify-center items-center p-4">
            <div className="absolute top-8">
                <BrandLogo />
            </div>
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="w-full max-w-md"
            >
                <div className="glass-high p-8 rounded-2xl shadow-2xl border border-white/10">
                    {!success ? (
                        <>
                            <h2 className="text-2xl font-bold text-white text-center mb-2">Activate Your Account</h2>
                            <p className="text-text-secondary text-center mb-8">Welcome! Set your username and password to join the team.</p>

                            <form onSubmit={handleSubmit} className="space-y-6">
                                {error && (
                                    <div className="bg-red-500/10 text-red-300 text-sm p-3 rounded-lg flex items-center gap-2">
                                        <AlertTriangle size={16} />
                                        <span>{error}</span>
                                    </div>
                                )}
                                <div>
                                    <label className="text-xs font-bold text-gray-400 uppercase">Username</label>
                                    <div className="relative mt-2">
                                        <User size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                        <input
                                            type="text"
                                            value={username}
                                            onChange={(e) => setUsername(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg"
                                            placeholder="Choose a username"
                                        />
                                    </div>
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-gray-400 uppercase">Password</label>
                                    <div className="relative mt-2">
                                        <KeyRound size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
                                        <input
                                            type="password"
                                            value={password}
                                            onChange={(e) => setPassword(e.target.value)}
                                            required
                                            className="glass-input w-full pl-10 pr-3 py-2.5 rounded-lg"
                                            placeholder="Minimum 8 characters"
                                        />
                                    </div>
                                </div>
                                <button
                                    type="submit"
                                    disabled={isLoading || !token}
                                    className="w-full bg-gradient-to-r from-primary-start to-primary-end text-white font-bold py-3 rounded-lg disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {isLoading ? <Loader2 className="animate-spin" /> : 'Create Account & Join'}
                                </button>
                            </form>
                        </>
                    ) : (
                        <div className="text-center">
                            <CheckCircle size={48} className="mx-auto text-emerald-400 mb-4" />
                            <h2 className="text-2xl font-bold text-white mb-2">Success!</h2>
                            <p className="text-text-secondary mb-6">{success}</p>
                            <p className="text-sm text-gray-500">Redirecting to login...</p>
                        </div>
                    )}
                </div>
            </motion.div>
        </div>
    );
};

export default AcceptInvitePage;