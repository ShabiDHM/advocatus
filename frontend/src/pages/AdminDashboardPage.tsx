// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V3.0 (GLASS & LOGIC)
// 1. VISUALS: Full Glassmorphism adoption (glass-panel, glass-high).
// 2. LOGIC: Preserved explicit payload construction for status updates.
// 3. UX: Improved responsive table layout and modal animations.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Search, Edit2, Trash2, CheckCircle, Loader2, Clock, ShieldAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
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
        setIsLoading(true);
        try {
            const rawData = await apiService.getAllUsers();
            const normalizedData = rawData.map((u: any) => ({
                ...u,
                id: u.id || u._id,
                role: u.role || 'STANDARD'
            }));
            const validUsers = normalizedData.filter((user: any) => user && typeof user.id === 'string' && user.id.trim() !== '');
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
            role: user.role || 'STANDARD',
            subscription_status: user.subscription_status || 'INACTIVE',
            status: (user as any).status || 'inactive'
        });
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser?.id) return;
        
        try {
            const isActive = editForm.subscription_status === 'ACTIVE';
            
            const payload: UpdateUserRequest = {
                username: editForm.username,
                email: editForm.email,
                role: editForm.role,
                subscription_status: editForm.subscription_status,
                status: isActive ? 'active' : 'inactive'
            };

            await apiService.updateUser(editingUser.id, payload);
            setEditingUser(null);
            loadUsers(); 
        } catch (error) {
            console.error("Failed to update user", error);
            alert(t('error.generic', 'An unexpected error occurred.'));
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm(t('admin.confirmDelete', 'Are you sure you want to delete this user? This action is irreversible.'))) return;
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

    const renderStatusBadge = (user: User) => {
        const status = user.subscription_status || 'INACTIVE';
        if (status === 'ACTIVE') {
            return <span className="flex items-center text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg text-xs font-bold w-fit"><CheckCircle className="w-3 h-3 mr-1.5" /> {t('admin.statuses.ACTIVE', 'Active')}</span>;
        }
        return <span className="flex items-center text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2.5 py-1 rounded-lg text-xs font-bold w-fit"><Clock className="w-3 h-3 mr-1.5" /> {t('admin.statuses.INACTIVE', 'Pending')}</span>;
    };

    if (isLoading) return <div className="flex justify-center items-center h-screen"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-screen">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2 tracking-tight flex items-center gap-3">
                    <ShieldAlert className="text-primary-start" size={32} />
                    {t('admin.title', 'Admin Panel')}
                </h1>
                <p className="text-text-secondary">{t('admin.subtitle', 'Manage users and system settings.')}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalUsers', 'Total Users')}</p><h3 className="text-3xl font-bold text-white">{users.length}</h3></div>
                    <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20"><Users size={24} /></div>
                </div>
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.pendingApproval', 'Pending Approval')}</p><h3 className="text-3xl font-bold text-amber-500">{users.filter(u => u.subscription_status === 'INACTIVE').length}</h3></div>
                    <div className="p-3 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20"><Clock size={24} /></div>
                </div>
            </div>

            <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white/5">
                    <h3 className="text-lg font-bold text-white">{t('admin.registeredUsers', 'Registered Users')}</h3>
                    <div className="relative w-full sm:w-auto">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
                        <input type="text" placeholder={t('admin.search', 'Search...')} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="glass-input pl-10 pr-4 py-2 w-full sm:w-64 text-sm rounded-xl" />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-text-secondary">
                        <thead className="bg-black/20 text-gray-400 uppercase text-xs font-bold">
                            <tr>
                                <th className="px-6 py-4 tracking-wider">{t('admin.table.user', 'User')}</th>
                                <th className="px-6 py-4 tracking-wider">{t('admin.table.role', 'Role')}</th>
                                <th className="px-6 py-4 tracking-wider">{t('admin.table.status', 'Status')}</th>
                                <th className="px-6 py-4 tracking-wider">{t('admin.table.registered', 'Registered')}</th>
                                <th className="px-6 py-4 text-right tracking-wider">{t('admin.table.actions', 'Actions')}</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredUsers.map((user) => (
                                <tr key={user.id} className="hover:bg-white/5 transition-colors group">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center">
                                            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-start to-primary-end flex items-center justify-center text-white font-bold mr-3 shadow-lg shadow-primary-start/20">
                                                {user.username.charAt(0).toUpperCase()}
                                            </div>
                                            <div>
                                                <div className="font-bold text-white">{user.username}</div>
                                                <div className="text-xs text-gray-500">{user.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4"><span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${user.role === 'ADMIN' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-blue-500/10 text-blue-400 border-blue-500/20'}`}>{user.role}</span></td>
                                    <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                    <td className="px-6 py-4 font-mono text-xs">{new Date(user.created_at).toLocaleDateString()}</td>
                                    <td className="px-6 py-4 text-right space-x-2">
                                        <button onClick={() => handleEditClick(user)} className="bg-white/5 hover:bg-white/10 text-white p-2 rounded-lg transition-colors border border-white/5 hover:border-white/20"><Edit2 className="w-4 h-4" /></button>
                                        <button onClick={() => handleDeleteUser(user.id)} className="bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 p-2 rounded-lg transition-colors border border-red-500/20"><Trash2 className="w-4 h-4" /></button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <AnimatePresence>
                {editingUser && (
                    <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <motion.div 
                            initial={{ scale: 0.95, opacity: 0 }} 
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.95, opacity: 0 }}
                            className="glass-high p-8 rounded-2xl w-full max-w-md shadow-2xl"
                        >
                            <h3 className="text-xl font-bold text-white mb-6 border-b border-white/10 pb-4">{t('admin.editModal.title', 'Edit User')}</h3>
                            <form onSubmit={handleUpdateUser} className="space-y-5">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('admin.editModal.username', 'Username')}</label>
                                    <input type="text" value={editForm.username || ''} onChange={e => setEditForm({ ...editForm, username: e.target.value })} className="glass-input w-full px-4 py-2.5 rounded-xl" />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('admin.editModal.email', 'Email')}</label>
                                    <input type="email" value={editForm.email || ''} onChange={e => setEditForm({ ...editForm, email: e.target.value })} className="glass-input w-full px-4 py-2.5 rounded-xl" />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('admin.editModal.role', 'Role')}</label>
                                        <select value={editForm.role || 'STANDARD'} onChange={e => setEditForm({ ...editForm, role: e.target.value })} className="glass-input w-full px-3 py-2.5 rounded-xl cursor-pointer">
                                            <option value="STANDARD" className="bg-gray-900 text-white">{t('admin.roles.STANDARD', 'User')}</option>
                                            <option value="ADMIN" className="bg-gray-900 text-white">{t('admin.roles.ADMIN', 'Admin')}</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5">{t('admin.editModal.accountStatus', 'Status')}</label>
                                        <select 
                                            value={editForm.subscription_status} 
                                            onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} 
                                            className={`glass-input w-full px-3 py-2.5 rounded-xl cursor-pointer font-bold ${editForm.subscription_status === 'ACTIVE' ? 'text-emerald-400' : 'text-amber-400'}`}
                                        >
                                            <option value="ACTIVE" className="bg-gray-900 text-white">{t('admin.statuses.ACTIVE', 'Active')}</option>
                                            <option value="INACTIVE" className="bg-gray-900 text-white">{t('admin.statuses.INACTIVE', 'Pending')}</option>
                                        </select>
                                    </div>
                                </div>
                                <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-white/10">
                                    <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 rounded-xl hover:bg-white/10 text-text-secondary hover:text-white transition-colors">{t('admin.editModal.cancel', 'Cancel')}</button>
                                    <button type="submit" className="px-6 py-2 rounded-xl bg-gradient-to-r from-primary-start to-primary-end text-white font-bold shadow-lg shadow-primary-start/20 transition-all active:scale-95">{t('admin.editModal.save', 'Save Changes')}</button>
                                </div>
                            </form>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default AdminDashboardPage;