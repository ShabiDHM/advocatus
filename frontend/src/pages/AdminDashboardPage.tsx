// FILE: /home/user/advocatus-frontend/src/pages/AdminDashboardPage.tsx
// DEFINITIVE VERSION 3.3 (SIGNATURE CORRECTION):
// Corrected the 'onUpdate' prop signature in the EditUserModal and its handler
// to accept two arguments, resolving the 'ts(2554)' build error.

import React, { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AdminUser, UpdateUserRequest } from '../data/types';
import { apiService } from '../services/api';
import { useTranslation } from 'react-i18next';
import { 
  Shield, Users, Search, Filter, Edit, Trash2, Crown, AlertCircle, RefreshCw, UserCheck, UserX, FileText
} from 'lucide-react';

// --- HELPER FUNCTIONS ---
const getRoleColor = (role: AdminUser['role']) => { switch (role) { case 'ADMIN': return 'text-purple-300 bg-purple-900/20 border-purple-600'; case 'LAWYER': return 'text-blue-300 bg-blue-900/20 border-blue-600'; default: return 'text-gray-300 bg-gray-900/20 border-gray-600'; } };
const getStatusColor = (status: AdminUser['subscription_status']) => { switch (status) { case 'ACTIVE': return 'text-green-300 bg-green-900/20 border-green-600'; case 'TRIAL': return 'text-blue-300 bg-blue-900/20 border-blue-600'; case 'expired': return 'text-red-300 bg-red-900/20 border-red-600'; default: return 'text-gray-300 bg-gray-900/20 border-gray-600'; } };
const formatDate = (dateString?: string) => { if (!dateString) return 'Never'; try { return new Date(dateString).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' }); } catch { return 'Invalid Date'; } };

// --- SUB-COMPONENTS ---

const StatCard: React.FC<{ icon: React.ReactNode, title: string, value: number | string }> = ({ icon, title, value }) => (
  <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl p-6 shadow-xl"><div className="flex items-center"><div className="flex-shrink-0">{icon}</div><div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-400 truncate">{title}</dt><dd className="text-2xl font-bold text-white">{value}</dd></dl></div></div></div>
);

interface UserRowProps { user: AdminUser; currentUserId: string; onEdit: (user: AdminUser) => void; onDelete: (user: AdminUser) => void; }
const UserRow: React.FC<UserRowProps> = ({ user, currentUserId, onEdit, onDelete }) => (
  <tr className="hover:bg-background-dark/30">
    <td className="px-6 py-4 whitespace-nowrap"><div><div className="text-sm font-medium text-white">{user.username}</div><div className="text-sm text-gray-400">{user.email || 'No email'}</div></div></td>
    <td className="px-6 py-4 whitespace-nowrap"><span className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold border ${getRoleColor(user.role)}`}>{user.role}</span></td>
    <td className="px-6 py-4 whitespace-nowrap"><span className={`inline-flex px-2 py-1 rounded-full text-xs font-semibold border ${getStatusColor(user.subscription_status)}`}>{user.subscription_status}</span></td>
    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{user.case_count || 0} / {user.document_count || 0}</td>
    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{formatDate(user.created_at)}</td>
    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-400">{formatDate(user.last_login)}</td>
    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium"><div className="flex items-center justify-end space-x-3"><button onClick={() => onEdit(user)} className="text-blue-400 hover:text-blue-300" title="Edit User"><Edit className="h-4 w-4" /></button><button onClick={() => onDelete(user)} disabled={currentUserId === user.id} className="text-red-400 hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed" title="Delete User"><Trash2 className="h-4 w-4" /></button></div></td>
  </tr>
);

interface EditUserModalProps { user: AdminUser; onUpdate: (userId: string, updateData: UpdateUserRequest) => void; onClose: () => void; isUpdating: boolean; t: (key: string, options?: any) => string; }
const EditUserModal: React.FC<EditUserModalProps> = ({ user, onUpdate, onClose, isUpdating, t }) => {
  const [formData, setFormData] = useState<UpdateUserRequest>({ subscription_status: user.subscription_status, role: user.role, email: user.email });
  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); onUpdate(user.id, formData); };
  return <div className="fixed inset-0 bg-black bg-opacity-70 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-background-dark/80 border border-glass-edge rounded-2xl p-6 w-full max-w-md shadow-2xl"><h2 className="text-xl font-semibold text-white mb-4">{t('admin.editUserTitle', { username: user.username })}</h2><form onSubmit={handleSubmit} className="space-y-4"><div><label className="block text-sm font-medium text-gray-300 mb-1">{t('auth.email')}</label><input type="email" value={formData.email || ''} onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))} className="block w-full px-3 py-2 border border-glass-edge rounded-xl bg-background-light/50 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500" placeholder={t('auth.email')}/></div><div><label className="block text-sm font-medium text-gray-300 mb-1">{t('admin.role')}</label><select value={formData.role} onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value as any }))} className="block w-full px-3 py-2 border border-glass-edge rounded-xl bg-background-light/50 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"><option value="STANDARD">Standard</option><option value="LAWYER">Lawyer</option><option value="ADMIN">Administrator</option></select></div><div><label className="block text-sm font-medium text-gray-300 mb-1">{t('admin.status')}</label><select value={formData.subscription_status} onChange={(e) => setFormData(prev => ({ ...prev, subscription_status: e.target.value as any }))} className="block w-full px-3 py-2 border border-glass-edge rounded-xl bg-background-light/50 text-white focus:outline-none focus:ring-2 focus:ring-purple-500"><option value="ACTIVE">Active</option><option value="TRIAL">Trial</option><option value="INACTIVE">Inactive</option><option value="expired">Expired</option></select></div><div className="flex space-x-3 pt-4"><button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-glass-edge rounded-md text-gray-300 hover:bg-background-light/50 transition duration-200">{t('dashboard.cancelButton')}</button><button type="submit" disabled={isUpdating} className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-md transition duration-200">{isUpdating ? t('admin.updating') : t('admin.updateUser')}</button></div></form></div></div>;
};

interface DeleteUserModalProps { user: AdminUser; onConfirm: () => void; onClose: () => void; isDeleting: boolean; t: (key: string, options?: any) => string; }
const DeleteUserModal: React.FC<DeleteUserModalProps> = ({ user, onConfirm, onClose, isDeleting, t }) => (
  <div className="fixed inset-0 bg-black bg-opacity-70 backdrop-blur-sm flex items-center justify-center p-4 z-50"><div className="bg-background-dark/80 border border-glass-edge rounded-2xl p-6 w-full max-w-md shadow-2xl"><div className="flex items-center mb-4"><AlertCircle className="h-6 w-6 text-red-400 mr-3" /><h2 className="text-xl font-semibold text-white">{t('admin.deleteUserTitle')}</h2></div><p className="text-gray-300 mb-6">{t('admin.confirmDeleteUserMessage', { username: user.username })}</p><div className="flex space-x-3"><button type="button" onClick={onClose} className="flex-1 px-4 py-2 border border-glass-edge rounded-md text-gray-300 hover:bg-background-light/50 transition duration-200">{t('dashboard.cancelButton')}</button><button onClick={onConfirm} disabled={isDeleting} className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white rounded-md transition duration-200">{isDeleting ? t('admin.deleting') : t('admin.deleteUser')}</button></div></div></div>
);

// --- MAIN COMPONENT ---
const AdminDashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | AdminUser['subscription_status']>('ALL');
  const [roleFilter, setRoleFilter] = useState<'ALL' | AdminUser['role']>('ALL');
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null);
  const [deletingUserId, setDeletingUserId] = useState<string | null>(null);

  if (!user || user.role !== 'ADMIN') { return <Navigate to="/dashboard" replace />; }

  useEffect(() => { loadUsers(); }, []);

  const loadUsers = async () => {
    try { setLoading(true); setError(''); const fetchedUsers = await apiService.getAllUsers(); setUsers(fetchedUsers); } 
    catch (error: any) { setError(error.response?.data?.message || error.message || t('admin.fetchUsersFailure')); } 
    finally { setLoading(false); }
  };

  const handleEditUser = (userToEdit: AdminUser) => { setSelectedUser(userToEdit); setIsEditModalOpen(true); };
  const handleDeleteUser = (userToDelete: AdminUser) => { setSelectedUser(userToDelete); setIsDeleteModalOpen(true); };

  // PHOENIX PROTOCOL FIX: Ensure handler signature matches the prop type
  const handleUpdateUser = async (userId: string, updateData: UpdateUserRequest) => {
    setUpdatingUserId(userId);
    try { const updatedUser = await apiService.updateUser(userId, updateData); setUsers(prev => prev.map(u => u.id === userId ? updatedUser : u)); setIsEditModalOpen(false); setSelectedUser(null); } 
    catch (error: any) { alert(error.response?.data?.message || t('admin.updateUserFailure')); } 
    finally { setUpdatingUserId(null); }
  };

  const handleConfirmDelete = async () => {
    if (!selectedUser) return;
    setDeletingUserId(selectedUser.id);
    try { await apiService.deleteUser(selectedUser.id); setUsers(prev => prev.filter(u => u.id !== selectedUser.id)); setIsDeleteModalOpen(false); setSelectedUser(null); } 
    catch (error: any) { alert(error.response?.data?.message || t('admin.deleteUserFailure')); } 
    finally { setDeletingUserId(null); }
  };

  const filteredUsers = users.filter(u => {
    const searchContent = `${u.username} ${u.email}`.toLowerCase();
    const matchesSearch = searchContent.includes(searchTerm.toLowerCase());
    const matchesStatus = statusFilter === 'ALL' || u.subscription_status === statusFilter;
    const matchesRole = roleFilter === 'ALL' || u.role === roleFilter;
    return matchesSearch && matchesStatus && matchesRole;
  });

  if (loading) { return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div></div>; }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 text-text-primary">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-8">
        <div className="flex items-center space-x-3"><div className="bg-purple-600 p-3 rounded-lg"><Shield className="h-6 w-6 text-white" /></div><div><h1 className="text-3xl font-bold text-white">{t('admin.pageTitle')}</h1><p className="text-gray-400 mt-1">{t('admin.pageSubtitle')}</p></div></div>
        <div className="mt-4 sm:mt-0 flex space-x-3"><button onClick={loadUsers} className="inline-flex items-center px-4 py-2 border border-glass-edge/50 rounded-xl shadow-sm text-sm font-medium text-gray-300 bg-background-light/50 hover:bg-background-dark/50 transition duration-200"><RefreshCw className="h-4 w-4 mr-2" />{t('admin.refresh')}</button></div>
      </div>
      {error && <div className="bg-red-900/50 border border-red-600 rounded-md p-4 mb-6 flex items-center space-x-2"><AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" /><span className="text-red-300">{error}</span></div>}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard icon={<Users className="h-8 w-8 text-blue-400" />} title={t('admin.totalUsers')} value={users.length} />
        <StatCard icon={<UserCheck className="h-8 w-8 text-green-400" />} title={t('admin.activeUsers')} value={users.filter(u => u.subscription_status === 'ACTIVE').length} />
        <StatCard icon={<Crown className="h-8 w-8 text-purple-400" />} title={t('admin.administrators')} value={users.filter(u => u.role === 'ADMIN').length} />
        <StatCard icon={<FileText className="h-8 w-8 text-yellow-400" />} title={t('admin.totalDocs')} value={users.reduce((sum, u) => sum + (u.document_count || 0), 0)} />
      </div>
      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 mb-6">
        <div className="flex-1 relative"><Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" /><input type="text" placeholder={t('admin.searchPlaceholder')} value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="block w-full pl-10 pr-3 py-2 border border-glass-edge rounded-xl bg-background-dark/50 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500" /></div>
        <div className="relative"><select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as any)} className="block w-full pl-3 pr-10 py-2 border border-glass-edge rounded-xl bg-background-dark/50 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 appearance-none"><option value="ALL">{t('admin.allStatuses')}</option><option value="ACTIVE">Active</option><option value="TRIAL">Trial</option><option value="INACTIVE">Inactive</option><option value="expired">Expired</option></select><Filter className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" /></div>
        <div className="relative"><select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as any)} className="block w-full pl-3 pr-10 py-2 border border-glass-edge rounded-xl bg-background-dark/50 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 appearance-none"><option value="ALL">{t('admin.allRoles')}</option><option value="ADMIN">Admin</option><option value="LAWYER">Lawyer</option><option value="STANDARD">Standard</option></select><Filter className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" /></div>
      </div>
      <div className="bg-background-light/50 backdrop-blur-md border border-glass-edge rounded-2xl shadow-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-glass-edge/50"><h2 className="text-lg font-semibold text-white">{t('admin.users')} ({filteredUsers.length})</h2></div>
        <div className="overflow-x-auto"><table className="min-w-full divide-y divide-glass-edge/50"><thead className="bg-background-dark/50"><tr><th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.user')}</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.role')}</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.status')}</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.casesDocs')}</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.created')}</th><th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.lastLogin')}</th><th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">{t('admin.actions')}</th></tr></thead><tbody className="divide-y divide-glass-edge/50">{filteredUsers.map((u) => <UserRow key={u.id} user={u} currentUserId={user.id} onEdit={handleEditUser} onDelete={handleDeleteUser} />)}</tbody></table>{filteredUsers.length === 0 && <div className="text-center py-12"><UserX className="mx-auto h-12 w-12 text-gray-400 mb-4" /><h3 className="text-lg font-medium text-gray-300 mb-2">{t('admin.noUsersFound')}</h3><p className="text-gray-400">{users.length === 0 ? t('admin.noUsersInSystem') : t('admin.adjustFilters')}</p></div>}</div>
      </div>
      {isEditModalOpen && selectedUser && <EditUserModal user={selectedUser} onUpdate={handleUpdateUser} onClose={() => { setIsEditModalOpen(false); setSelectedUser(null); }} isUpdating={updatingUserId === selectedUser.id} t={t} />}
      {isDeleteModalOpen && selectedUser && <DeleteUserModal user={selectedUser} onConfirm={handleConfirmDelete} onClose={() => { setIsDeleteModalOpen(false); setSelectedUser(null); }} isDeleting={deletingUserId === selectedUser.id} t={t} />}
    </div>
  );
};

export default AdminDashboardPage;