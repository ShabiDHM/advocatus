// FILE: src/pages/JoinPage.tsx
// PHOENIX PROTOCOL - JOIN PAGE V1.0
// 1. PURPOSE: Landing page for invitation links.
// 2. LOGIC: Extracts token, accepts credentials, calls joinOrganization().

import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { UserPlus, Lock, User, Loader2, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';
import { useAuth } from '../context/AuthContext'; // To trigger login refresh

const JoinPage: React.FC = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { refreshUser } = useAuth();
    
    const token = searchParams.get('token');
    
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Redirect if no token
    useEffect(() => {
        if (!token) {
            navigate('/login');
        }
    }, [token, navigate]);

    const handleJoin = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!token) return;
        
        setLoading(true);
        setError(null);

        try {
            await apiService.joinOrganization(token, username, password);
            // Success: Token is already set in api.ts, just update context and redirect
            await refreshUser();
            navigate('/dashboard'); 
        } catch (err: any) {
            console.error(err);
            setError(err.response?.data?.detail || "Failed to join organization. Link may be expired.");
        } finally {
            setLoading(false);
        }
    };

    if (!token) return null;

    return (
        <div className="min-h-screen bg-background-dark flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary-start/20 via-background-dark to-background-dark z-0 pointer-events-none" />
            
            <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass-panel w-full max-w-md p-8 rounded-3xl relative z-10 shadow-2xl"
            >
                <div className="text-center mb-8">
                    <div className="w-16 h-16 bg-primary-start/20 rounded-2xl flex items-center justify-center mx-auto mb-4 text-primary-start">
                        <UserPlus size={32} />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-2">Join the Team</h1>
                    <p className="text-text-secondary text-sm">Create your account to accept the invitation.</p>
                </div>

                <form onSubmit={handleJoin} className="space-y-6">
                    {error && (
                        <div className="p-4 rounded-xl bg-red-500/20 border border-red-500/30 text-red-200 text-sm flex items-start gap-3">
                            <AlertTriangle className="flex-shrink-0 mt-0.5" size={16} />
                            <span>{error}</span>
                        </div>
                    )}

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase">Full Name</label>
                        <div className="relative">
                            <User className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                            <input 
                                type="text" 
                                required
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white"
                                placeholder="John Doe"
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-xs font-bold text-gray-500 uppercase">Set Password</label>
                        <div className="relative">
                            <Lock className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                            <input 
                                type="password" 
                                required
                                minLength={8}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="glass-input w-full pl-12 pr-4 py-3 rounded-xl text-white"
                                placeholder="••••••••"
                            />
                        </div>
                    </div>

                    <button 
                        type="submit" 
                        disabled={loading}
                        className="w-full py-4 bg-gradient-to-r from-primary-start to-primary-end text-white rounded-xl font-bold text-lg hover:shadow-lg hover:shadow-primary-start/20 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-wait flex items-center justify-center gap-2"
                    >
                        {loading ? <Loader2 className="animate-spin" /> : "Complete Registration"}
                    </button>
                </form>
            </motion.div>
        </div>
    );
};

export default JoinPage;