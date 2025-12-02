// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - BUILD REPAIR
// 1. FIX: Added missing 'motion' import.
// 2. CLEANUP: Removed unused 'Shield' import.
// 3. LOGIC: Preserved Gatekeeper 'subscription_status' workflow.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Search, Edit2, Trash2, CheckCircle, XCircle, Loader2, Clock } from 'lucide-react';
import { motion } from 'framer-motion'; // <--- FIX: Added this import
import { apiService } from '../services/api';
import { User, UpdateUserRequest } from '../data/types';

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [users, setUsers] = useState<User[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [editForm, setEditForm] = useState<UpdateUserRequest>({});

    useEffect(() => {
        loadUsers();
    }, []);

    const loadUsers = async () => {
        try {
            const rawData = await apiService.getAllUsers();
            
            // Normalize Data (Handle _id vs id)
            const normalizedData = rawData.map((u: any) => ({
                ...u,
                id: u.id || u._id // Fallback to _id if id is missing
            }));

            const validUsers = normalizedData.filter((user: any) => 
                user && typeof user.id === 'string' && user.id.trim() !== ''
            );
            
            setUsers(validUsers);

        } catch (error) {
            console.error("Failed to load users", error);
            setUsers([]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleEditClick = (user: User) => {
        setEditingUser(user);
        setEditForm({
            username: user.username,
            email: user.email,
            role: user.role,
            // Map subscription_status correctly (default to INACTIVE if missing)
            subscription_status: user.subscription_status || 'INACTIVE',
            status: user.status // Keep legacy status just in case
        });
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser?.id) return;

        try {
            await apiService.updateUser(editingUser.id, editForm);
            setEditingUser(null);
            loadUsers(); // Reload to show updated status
        } catch (error) {
            console.error("Failed to update user", error);
            alert(t('error.generic'));
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm(t('admin.confirmDelete'))) return;
        try {
            await apiService.deleteUser(userId);
            loadUsers();
        } catch (error) {
            console.error("Failed to delete user", error);
        }
    };

    const filteredUsers = users.filter(u =>
        u.username?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Helper to render status badge
    const renderStatusBadge = (user: User) => {
        // The backend checks subscription_status for login access
        const status = user.subscription_status || 'INACTIVE';
        
        if (status === 'ACTIVE') {
            return <span className="flex items-center text-green-400 bg-green-400/10 px-2 py-1 rounded-full text-xs font-medium w-fit"><CheckCircle className="w-3 h-3 mr-1" /> Aktiv</span>;
        } else if (status === 'INACTIVE') {
            return <span className="flex items-center text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded-full text-xs font-medium w-fit"><Clock className="w-3 h-3 mr-1" /> Në Pritje</span>;
        } else {
             return <span className="flex items-center text-red-400 bg-red-400/10 px-2 py-1 rounded-full text-xs font-medium w-fit"><XCircle className="w-3 h-3 mr-1" /> Pezulluar</span>;
        }
    };

    if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-text-primary mb-2">{t('admin.title', 'Paneli i Administratorit')}</h1>
                <p className="text-text-secondary">{t('admin.subtitle', 'Menaxhimi i përdoruesve dhe sistemit.')}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-sm font-medium">Total Users</p><h3 className="text-3xl font-bold text-white">{users.length}</h3></div>
                    <div className="p-3 rounded-xl bg-blue-500/20 text-blue-400"><Users /></div>
                </div>
                <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between shadow-lg">
                    <div><p className="text-text-secondary text-sm font-medium">Pending Approval</p><h3 className="text-3xl font-bold text-yellow-500">{users.filter(u => u.subscription_status === 'INACTIVE').length}</h3></div>
                    <div className="p-3 rounded-xl bg-yellow-500/20 text-yellow-400"><Clock /></div>
                </div>
            </div>

            <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge overflow-hidden shadow-xl">
                <div className="p-4 border-b border-glass-edge flex justify-between items-center bg-white/5">
                    <h3 className="text-lg font-semibold text-white">Përdoruesit e Regjistruar</h3>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
                        <input type="text" placeholder="Kërko..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 pr-4 py-2 bg-black/40 border border-white/10 rounded-lg text-sm text-white focus:ring-1 focus:ring-primary-start outline-none" />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-text-secondary">
                        <thead className="bg-black/20 text-text-primary uppercase text-xs">
                            <tr>
                                <th className="px-6 py-3 font-semibold tracking-wider">Përdoruesi</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">Roli</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">Statusi (Gatekeeper)</th>
                                <th className="px-6 py-3 font-semibold tracking-wider">Regjistruar</th>
                                <th className="px-6 py-3 text-right font-semibold tracking-wider">Veprime</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredUsers.map((user) => (
                                <tr key={user.id} className="hover:bg-white/5 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center">
                                            <div className="w-8 h-8 rounded-full bg-primary-start/20 flex items-center justify-center text-primary-start font-bold mr-3 border border-primary-start/30">
                                                {user.username.charAt(0).toUpperCase()}
                                            </div>
                                            <div>
                                                <div className="font-medium text-white">{user.username}</div>
                                                <div className="text-xs text-gray-500">{user.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs font-medium border ${user.role === 'ADMIN' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{user.role}</span></td>
                                    <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                    <td className="px-6 py-4">{new Date(user.created_at).toLocaleDateString()}</td>
                                    <td className="px-6 py-4 text-right space-x-2">
                                        <button onClick={() => handleEditClick(user)} className="bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 p-2 rounded-lg transition-colors border border-blue-500/20"><Edit2 className="w-4 h-4" /></button>
                                        <button onClick={() => handleDeleteUser(user.id)} className="bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 p-2 rounded-lg transition-colors border border-red-500/20"><Trash2 className="w-4 h-4" /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {editingUser && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <motion.div 
                        initial={{ scale: 0.95, opacity: 0 }} 
                        animate={{ scale: 1, opacity: 1 }} 
                        className="bg-[#1f2937] border border-white/10 p-6 rounded-2xl w-full max-w-md shadow-2xl"
                    >
                        <h3 className="text-xl font-bold text-white mb-6 border-b border-white/10 pb-4">Modifiko Përdoruesin</h3>
                        <form onSubmit={handleUpdateUser} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Username</label>
                                <input type="text" value={editForm.username || ''} onChange={e => setEditForm({ ...editForm, username: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none" />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Email</label>
                                <input type="email" value={editForm.email || ''} onChange={e => setEditForm({ ...editForm, email: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none" />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Roli</label>
                                    <select value={editForm.role || 'LAWYER'} onChange={e => setEditForm({ ...editForm, role: e.target.value })} className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:border-primary-start outline-none">
                                        <option value="LAWYER">Lawyer</option>
                                        <option value="ADMIN">Admin</option>
                                        <option value="CLIENT">Client</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-medium text-gray-400 uppercase mb-1">Llogaria (Gatekeeper)</label>
                                    {/* Editing subscription_status directly */}
                                    <select 
                                        value={editForm.subscription_status} 
                                        onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} 
                                        className={`w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 focus:border-primary-start outline-none font-bold ${editForm.subscription_status === 'ACTIVE' ? 'text-green-400' : 'text-yellow-400'}`}
                                    >
                                        <option value="ACTIVE">AKTIV (Lejohet)</option>
                                        <option value="INACTIVE">NË PRITJE (Bllokuar)</option>
                                    </select>
                                </div>
                            </div>
                            <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-white/10">
                                <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors">Anulo</button>
                                <button type="submit" className="px-6 py-2 rounded-lg bg-primary-start hover:bg-primary-end text-white font-semibold shadow-lg shadow-primary-start/20 transition-all">Ruaj Ndryshimet</button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboardPage;