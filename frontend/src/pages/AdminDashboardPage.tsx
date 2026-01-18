// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V4.3 (CLEANUP)
// 1. FIX: Removed local 'AdminApiService' type hack.
// 2. LOGIC: Now directly and correctly calls methods on the updated 'apiService'.

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Search, Loader2, ShieldAlert, ChevronsUpDown, Crown, ArrowUpCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiService } from '../services/api';
import { User, Organization } from '../data/types';

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [organizations, setOrganizations] = useState<Organization[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [upgradingOrg, setUpgradingOrg] = useState<Organization | null>(null);
    const [users, setUsers] = useState<User[]>([]); // For stats card
    const [showLegacyUsers, setShowLegacyUsers] = useState(false);

    useEffect(() => {
        loadAdminData();
    }, []);

    const loadAdminData = async () => {
        setIsLoading(true);
        try {
            const orgData = await apiService.getOrganizations();
            setOrganizations(orgData);

            const userData = await apiService.getAllUsers();
            setUsers(userData.filter((user) => user && typeof user.id === 'string' && user.id.trim() !== ''));
        } catch (error) {
            console.error("Failed to load admin data", error);
        } finally {
            setIsLoading(false);
        }
    };

    const handleUpgradeTier = async () => {
        if (!upgradingOrg) return;
        try {
            await apiService.upgradeOrganizationTier(upgradingOrg.id, 'TIER_2');
            setUpgradingOrg(null);
            loadAdminData(); // Refresh data after update
        } catch (error) {
            console.error("Failed to upgrade tier", error);
            alert('Upgrade failed. Check console for details.');
        }
    };
    
    const filteredOrgs = organizations.filter(org => 
        org.name?.toLowerCase().includes(searchQuery.toLowerCase())
    );

    if (isLoading) return <div className="flex justify-center items-center h-screen"><Loader2 className="animate-spin h-12 w-12 text-primary-start" /></div>;

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 min-h-screen">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2 tracking-tight flex items-center gap-3">
                    <ShieldAlert className="text-primary-start" size={32} />
                    {t('admin.title', 'Admin Panel')}
                </h1>
                <p className="text-text-secondary">{t('admin.subtitle', 'Manage organizations and system settings.')}</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalOrgs', 'Total Firms')}</p><h3 className="text-3xl font-bold text-white">{organizations.length}</h3></div>
                    <div className="p-3 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20"><Crown size={24} /></div>
                </div>
                <div className="glass-panel p-6 rounded-2xl flex items-center justify-between">
                    <div><p className="text-text-secondary text-xs font-bold uppercase tracking-wider mb-1">{t('admin.totalUsers', 'Total Users')}</p><h3 className="text-3xl font-bold text-white">{users.length}</h3></div>
                    <div className="p-3 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20"><Users size={24} /></div>
                </div>
            </div>

            <div className="glass-panel rounded-2xl overflow-hidden shadow-2xl">
                <div className="p-5 border-b border-white/5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white/5">
                    <h3 className="text-lg font-bold text-white">{t('admin.organizations', 'Organizations')}</h3>
                    <div className="relative w-full sm:w-auto">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-secondary" />
                        <input type="text" placeholder={t('admin.searchOrgs', 'Search firms...')} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="glass-input pl-10 pr-4 py-2 w-full sm:w-64 text-sm rounded-xl" />
                    </div>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm text-text-secondary">
                        <thead className="bg-black/20 text-gray-400 uppercase text-xs font-bold">
                            <tr>
                                <th className="px-6 py-4 tracking-wider">Firm Name</th>
                                <th className="px-6 py-4 tracking-wider">Tier</th>
                                <th className="px-6 py-4 tracking-wider">Seat Usage</th>
                                <th className="px-6 py-4 tracking-wider">Owner ID</th>
                                <th className="px-6 py-4 text-right tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {filteredOrgs.map((org) => (
                                <tr key={org.id} className="hover:bg-white/5 transition-colors group">
                                    <td className="px-6 py-4 font-bold text-white">{org.name}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2.5 py-1 rounded-lg text-xs font-bold border ${org.tier === 'TIER_2' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}>
                                            {org.tier}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 font-mono">{org.current_member_count} / {org.max_seats}</td>
                                    <td className="px-6 py-4 font-mono text-xs text-gray-500">{org.owner_id}</td>
                                    <td className="px-6 py-4 text-right">
                                        {org.tier !== 'TIER_2' && (
                                            <button onClick={() => setUpgradingOrg(org)} className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 p-2 rounded-lg transition-colors border border-emerald-500/20 flex items-center gap-2 text-xs font-bold">
                                                <ArrowUpCircle className="w-4 h-4" /> Upgrade
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div className="mt-8">
                 <button onClick={() => setShowLegacyUsers(!showLegacyUsers)} className="w-full glass-panel p-4 rounded-xl flex justify-between items-center hover:bg-white/5">
                    <h3 className="text-lg font-bold text-gray-400">Legacy User Management</h3>
                    <ChevronsUpDown className={`text-gray-500 transition-transform ${showLegacyUsers ? 'rotate-180' : ''}`} />
                </button>
                <AnimatePresence>
                {showLegacyUsers && <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden mt-4">
                    {/* The legacy user table would go here if needed */}
                </motion.div>}
                </AnimatePresence>
            </div>

            <AnimatePresence>
                {upgradingOrg && (
                     <div className="fixed inset-0 bg-background-dark/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                         <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }} className="glass-high p-8 rounded-2xl w-full max-w-md shadow-2xl">
                             <h3 className="text-xl font-bold text-white mb-2">Confirm Upgrade</h3>
                             <p className="text-text-secondary mb-6">Upgrade <span className="font-bold text-white">{upgradingOrg.name}</span> to TIER_2 (5 seats)?</p>
                             <div className="flex justify-end gap-3">
                                 <button onClick={() => setUpgradingOrg(null)} className="px-4 py-2 rounded-xl hover:bg-white/10 text-text-secondary hover:text-white transition-colors">Cancel</button>
                                 <button onClick={handleUpgradeTier} className="px-6 py-2 rounded-xl bg-gradient-to-r from-primary-start to-primary-end text-white font-bold">Confirm & Upgrade</button>
                             </div>
                         </motion.div>
                     </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default AdminDashboardPage;