// FILE: src/pages/AdminSupportPage.tsx
// PHOENIX PROTOCOL - ADMIN SUPPORT PAGE (REPLY TO SUPPORT MESSAGES)

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion';
import { Mail, Reply, Loader2, CheckCircle, AlertTriangle } from 'lucide-react';
import { apiService } from '../services/api';

interface SupportMessage {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    message: string;
    created_at: string;
    replied: boolean;
}

const AdminSupportPage: React.FC = () => {
    useTranslation();
    const [messages, setMessages] = useState<SupportMessage[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [replyingTo, setReplyingTo] = useState<SupportMessage | null>(null);
    const [replyText, setReplyText] = useState('');
    const [isSending, setIsSending] = useState(false);
    const [success, setSuccess] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadMessages();
    }, []);

    const loadMessages = async () => {
        try {
            const data = await apiService.getSupportMessages();
            setMessages(data);
        } catch (err) {
            console.error(err);
            setError('Failed to load support messages.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleReply = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!replyingTo || !replyText.trim()) return;
        setIsSending(true);
        setError(null);
        setSuccess(null);
        try {
            await apiService.sendSupportReply(replyingTo.email, replyText, replyingTo.id);
            setSuccess('Reply sent successfully.');
            setReplyingTo(null);
            setReplyText('');
            loadMessages(); // Refresh to update "replied" status
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to send reply.');
        } finally {
            setIsSending(false);
        }
    };

    if (isLoading) {
        return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-2">Support Messages</h1>
                <p className="text-text-secondary">Reply to customer inquiries.</p>
            </div>

            <div className="glass-panel rounded-2xl border border-main overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead className="bg-surface/30 text-text-primary uppercase text-xs font-bold border-b border-main">
                            <tr>
                                <th className="px-6 py-4">From</th>
                                <th className="px-6 py-4">Email</th>
                                <th className="px-6 py-4">Message</th>
                                <th className="px-6 py-4">Date</th>
                                <th className="px-6 py-4 text-center">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-main">
                            {messages.map((msg) => (
                                <tr key={msg.id} className="hover:bg-surface/20 transition-colors">
                                    <td className="px-6 py-4 font-medium text-text-primary">
                                        {msg.first_name} {msg.last_name}
                                    </td>
                                    <td className="px-6 py-4 text-text-secondary">{msg.email}</td>
                                    <td className="px-6 py-4 text-text-secondary max-w-md truncate">
                                        {msg.message}
                                    </td>
                                    <td className="px-6 py-4 text-text-secondary">
                                        {new Date(msg.created_at).toLocaleString()}
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <button
                                            onClick={() => setReplyingTo(msg)}
                                            className="p-2 bg-primary-start/10 text-primary-start rounded-lg border border-primary-start/20 hover:bg-primary-start/20 transition-colors"
                                            title="Reply"
                                            disabled={msg.replied}
                                        >
                                            <Reply size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Reply Modal */}
            {replyingTo && (
                <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="glass-panel max-w-lg w-full p-6 rounded-2xl border border-main"
                    >
                        <h2 className="text-xl font-bold text-text-primary mb-4">
                            Reply to {replyingTo.first_name} {replyingTo.last_name}
                        </h2>
                        <p className="text-sm text-text-secondary mb-2">
                            <span className="font-semibold">Email:</span> {replyingTo.email}
                        </p>
                        <p className="text-sm text-text-secondary mb-4 border-l-4 border-primary-start pl-3 italic">
                            "{replyingTo.message}"
                        </p>
                        <form onSubmit={handleReply}>
                            <textarea
                                value={replyText}
                                onChange={(e) => setReplyText(e.target.value)}
                                rows={5}
                                className="glass-input w-full p-3 rounded-xl border border-main bg-surface focus:border-primary-start"
                                placeholder="Type your reply here..."
                                required
                            />
                            {error && (
                                <div className="mt-3 text-danger-start text-sm flex items-center gap-2">
                                    <AlertTriangle size={14} /> {error}
                                </div>
                            )}
                            {success && (
                                <div className="mt-3 text-success-start text-sm flex items-center gap-2">
                                    <CheckCircle size={14} /> {success}
                                </div>
                            )}
                            <div className="flex justify-end gap-3 mt-6">
                                <button
                                    type="button"
                                    onClick={() => setReplyingTo(null)}
                                    className="px-4 py-2 text-text-secondary hover:text-text-primary transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    disabled={isSending || !replyText.trim()}
                                    className="btn-primary px-6 py-2 rounded-xl font-bold flex items-center gap-2"
                                >
                                    {isSending ? <Loader2 className="animate-spin h-4 w-4" /> : <Mail size={16} />}
                                    Send Reply
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminSupportPage;