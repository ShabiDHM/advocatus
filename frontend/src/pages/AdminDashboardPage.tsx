// FILE: src/pages/AdminDashboardPage.tsx
import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Search, Edit2, Trash2, Shield, CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { apiService } from '../services/api';
import { User, UpdateUserRequest } from '../data/types'; // Removed AdminUser, using User

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
      const data = await apiService.getAllUsers();
      setUsers(data);
    } catch (error) {
      console.error("Failed to load users", error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditClick = (user: User) => {
    setEditingUser(user);
    setEditForm({
      full_name: user.full_name,
      email: user.email,
      role: user.role,
      subscription_status: user.subscription_status || 'active',
      is_active: user.is_active
    });
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    
    try {
      await apiService.updateUser(editingUser.id, editForm);
      setEditingUser(null);
      loadUsers();
      alert(t('admin.userUpdated'));
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
    u.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (isLoading) return <div className="flex justify-center py-12"><Loader2 className="animate-spin h-8 w-8 text-primary-start" /></div>;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-text-primary mb-2">{t('admin.title', 'Paneli i Administratorit')}</h1>
        <p className="text-text-secondary">{t('admin.subtitle', 'Menaxhimi i përdoruesve dhe sistemit.')}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between">
          <div>
            <p className="text-text-secondary text-sm font-medium">Total Users</p>
            <h3 className="text-3xl font-bold text-white">{users.length}</h3>
          </div>
          <div className="p-3 rounded-xl bg-blue-500/20 text-blue-400"><Users /></div>
        </div>
        <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge flex items-center justify-between">
          <div>
            <p className="text-text-secondary text-sm font-medium">Active Lawyers</p>
            <h3 className="text-3xl font-bold text-white">{users.filter(u => u.role === 'LAWYER').length}</h3>
          </div>
          <div className="p-3 rounded-xl bg-purple-500/20 text-purple-400"><Shield /></div>
        </div>
      </div>

      {/* User Table */}
      <div className="bg-background-light/10 backdrop-blur-md rounded-2xl border border-glass-edge overflow-hidden">
        <div className="p-4 border-b border-glass-edge flex justify-between items-center">
          <h3 className="text-lg font-semibold text-white">Përdoruesit e Regjistruar</h3>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
            <input 
              type="text" 
              placeholder="Kërko..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-background-dark border border-glass-edge rounded-lg text-sm text-white focus:ring-1 focus:ring-primary-start outline-none"
            />
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-text-secondary">
            <thead className="bg-white/5 text-text-primary uppercase text-xs">
              <tr>
                <th className="px-6 py-3">Përdoruesi</th>
                <th className="px-6 py-3">Roli</th>
                <th className="px-6 py-3">Statusi</th>
                <th className="px-6 py-3">Regjistruar</th>
                <th className="px-6 py-3 text-right">Veprime</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-glass-edge">
              {filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-white">{user.full_name}</div>
                    <div className="text-xs">{user.email}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${user.role === 'ADMIN' ? 'bg-purple-500/20 text-purple-400' : 'bg-blue-500/20 text-blue-400'}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {user.is_active ? 
                      <span className="flex items-center text-green-400"><CheckCircle className="w-4 h-4 mr-1" /> Aktiv</span> : 
                      <span className="flex items-center text-red-400"><XCircle className="w-4 h-4 mr-1" /> Inaktiv</span>
                    }
                  </td>
                  <td className="px-6 py-4">{new Date(user.created_at).toLocaleDateString()}</td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button onClick={() => handleEditClick(user)} className="text-blue-400 hover:text-blue-300 p-1"><Edit2 className="w-4 h-4" /></button>
                    <button onClick={() => handleDeleteUser(user.id)} className="text-red-400 hover:text-red-300 p-1"><Trash2 className="w-4 h-4" /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      {editingUser && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-background-dark border border-glass-edge p-6 rounded-2xl w-full max-w-md shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-4">Modifiko Përdoruesin</h3>
            <form onSubmit={handleUpdateUser} className="space-y-4">
              <div>
                <label className="block text-sm text-text-secondary mb-1">Emri i Plotë</label>
                <input type="text" value={editForm.full_name} onChange={e => setEditForm({...editForm, full_name: e.target.value})} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white" />
              </div>
              <div>
                <label className="block text-sm text-text-secondary mb-1">Email</label>
                <input type="email" value={editForm.email} onChange={e => setEditForm({...editForm, email: e.target.value})} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-text-secondary mb-1">Roli</label>
                  <select value={editForm.role} onChange={e => setEditForm({...editForm, role: e.target.value})} className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white">
                    <option value="LAWYER">Lawyer</option>
                    <option value="ADMIN">Admin</option>
                    <option value="CLIENT">Client</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-text-secondary mb-1">Statusi</label>
                  <select 
                    value={editForm.is_active ? 'active' : 'inactive'} 
                    onChange={e => setEditForm({...editForm, is_active: e.target.value === 'active'})} 
                    className="w-full bg-background-light/10 border border-glass-edge rounded-lg px-4 py-2 text-white"
                  >
                    <option value="active">Aktiv</option>
                    <option value="inactive">Inaktiv</option>
                  </select>
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-6">
                <button type="button" onClick={() => setEditingUser(null)} className="px-4 py-2 rounded-lg hover:bg-white/10 text-text-secondary">Anulo</button>
                <button type="submit" className="px-6 py-2 rounded-lg bg-primary-start hover:bg-primary-end text-white font-semibold">Ruaj</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboardPage;