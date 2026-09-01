// FILE: src/pages/AdminDashboardPage.tsx
// PHOENIX PROTOCOL - ADMIN DASHBOARD V50.0 (1-CLICK CASE UNLOCK & MULTI-PAYMENT MANAGEMENT)

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
    Search, Edit2, Trash2, CheckCircle, Loader2, Clock, 
    Briefcase, AlertTriangle, Building2, User as UserIcon, Star, Mail, Key, ShieldAlert, Filter,
    Unlock, Lock, CreditCard, Banknote, RefreshCw, DollarSign, FolderGit2
} from 'lucide-react';
import { motion } from 'framer-motion';
import DatePicker from 'react-datepicker';
import "react-datepicker/dist/react-datepicker.css";
import { apiService } from '../services/api';
import { User, UpdateUserRequest } from '../data/types';
import { AccountType, ProductPlan } from '../data/enums';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

type UnifiedAdminUser = User & { 
    firmName?: string; 
    expiry_date?: Date | null;
    plan_tier?: 'DEFAULT' | 'GROWTH';
    user_limit?: number;
};

type AdminCaseView = {
    _id: string;
    title: string;
    client_name: string;
    client_position: string;
    is_unlocked: boolean;
    unlocked_at?: string;
    unlock_payment_method?: string;
    unlock_amount?: number;
    owner_email?: string;
    owner_name?: string;
    owner_role?: string;
    document_count: number;
    created_at?: string;
};

type MainTab = 'CASES_PAYMENTS' | 'USERS';
type UserRole = 'ADMIN' | 'LAWYER' | 'CLIENT' | 'STANDARD';
type StatusFilter = 'ALL' | 'ACTIVE' | 'PENDING' | 'INACTIVE_EXPIRED' | 'TEAM';
type CaseStatusFilter = 'ALL' | 'LOCKED' | 'UNLOCKED';

const AdminDashboardPage: React.FC = () => {
    const { t } = useTranslation();
    const [activeTab, setActiveTab] = useState<MainTab>('CASES_PAYMENTS');
    
    // Users State
    const [users, setUsers] = useState<UnifiedAdminUser[]>([]);
    const [isLoadingUsers, setIsLoadingUsers] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
    const [editingUser, setEditingUser] = useState<UnifiedAdminUser | null>(null);
    const [editForm, setEditForm] = useState<Partial<UnifiedAdminUser> & { expiry_date?: Date | null }>({});

    // Cases & Payments State
    const [cases, setCases] = useState<AdminCaseView[]>([]);
    const [isLoadingCases, setIsLoadingCases] = useState(false);
    const [caseSearchQuery, setCaseSearchQuery] = useState('');
    const [caseFilter, setCaseFilter] = useState<CaseStatusFilter>('ALL');
    const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

    useLockBodyScroll(!!editingUser);

    useEffect(() => {
        loadAdminData();
        loadCasesData();
    }, []);

    const loadAdminData = async () => {
        setIsLoadingUsers(true);
        try {
            const userData = await apiService.getAllUsers();
            const mappedUsers: UnifiedAdminUser[] = (userData || []).map((user: any) => ({
                ...user,
                id: user.id || user._id,
                firmName: user.organization_name,
                expiry_date: user.subscription_expiry ? new Date(user.subscription_expiry) : null,
                plan_tier: user.plan_tier || (user.product_plan === ProductPlan.TEAM_PLAN ? 'GROWTH' : 'DEFAULT'),
                user_limit: user.user_limit || (user.product_plan === ProductPlan.TEAM_PLAN ? 5 : 1) 
            })).filter((user: any) => user && typeof user.id === 'string' && user.id.trim() !== '');

            mappedUsers.sort((a, b) => getStatusScore(a) - getStatusScore(b));
            setUsers(mappedUsers);
        } catch (error) {
            console.error("Failed to load admin data", error);
        } finally {
            setIsLoadingUsers(false);
        }
    };

    const loadCasesData = async () => {
        setIsLoadingCases(true);
        try {
            // Thirrje e drejtpërdrejtë te endpoint-i i ri /admin/cases
            const response = await (apiService as any).getAdminCases?.() || await fetch('/api/admin/cases', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                    'Content-Type': 'application/json'
                }
            }).then(r => r.json());

            if (Array.isArray(response)) {
                setCases(response);
            }
        } catch (error) {
            console.error("Failed to load cases data", error);
        } finally {
            setIsLoadingCases(false);
        }
    };

    const getStatusScore = (user: UnifiedAdminUser) => {
        if (user.status === 'pending_invite') return 1;
        if (user.subscription_status !== 'ACTIVE' || user.status === 'inactive') return 0; 
        return 2; 
    };

    // =========================================================================
    // 🔓 VEPRIMET ME 1 KLIKIM PËR ZHBLLOKIMIN E LËNDËVE (CASH / MBANKING)
    // =========================================================================
    const handleUnlockCase = async (caseId: string, paymentMethod: 'CASH' | 'MBANKING' | 'CARD' = 'CASH', amount: number = 9.99) => {
        setActionLoadingId(caseId);
        try {
            const token = localStorage.getItem('token') || '';
            const res = await fetch(`/api/admin/cases/${caseId}/unlock`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    payment_method: paymentMethod,
                    amount: amount,
                    note: `Zhbllokuar me ${paymentMethod} nga Paneli i Adminit`
                })
            });

            if (res.ok) {
                // Përditëso gjendjen lokalisht në sekondë
                setCases(prev => prev.map(c => c._id === caseId ? { 
                    ...c, 
                    is_unlocked: true, 
                    unlock_payment_method: paymentMethod,
                    unlock_amount: amount,
                    unlocked_at: new Date().toISOString()
                } : c));
            } else {
                const err = await res.json();
                alert(err.detail || "Dështoi zhbllokimi i lëndës.");
            }
        } catch (error) {
            console.error("Unlock error:", error);
            alert("Ndodhi një gabim gjatë zhbllokimit.");
        } finally {
            setActionLoadingId(null);
        }
    };

    const handleLockCase = async (caseId: string) => {
        if (!window.confirm("A jeni të sigurt që dëshironi ta bllokoni përsëri këtë lëndë?")) return;
        setActionLoadingId(caseId);
        try {
            const token = localStorage.getItem('token') || '';
            const res = await fetch(`/api/admin/cases/${caseId}/lock`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (res.ok) {
                setCases(prev => prev.map(c => c._id === caseId ? { ...c, is_unlocked: false } : c));
            }
        } catch (error) {
            console.error("Lock error:", error);
        } finally {
            setActionLoadingId(null);
        }
    };

    const handleEditClick = (user: UnifiedAdminUser) => {
        setEditingUser(user);
        setEditForm({
            ...user,
            expiry_date: user.expiry_date
        });
    };

    const handleUpdateUser = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!editingUser?.id) return;
        
        try {
            const userUpdatePayload: UpdateUserRequest = {
                username: editForm.username,
                email: editForm.email,
                role: editForm.role,
                status: editForm.status,
                account_type: editForm.account_type,
                subscription_tier: 'PRO' as any,
                product_plan: editForm.product_plan,
                subscription_status: editForm.subscription_status,
                subscription_expiry: editForm.expiry_date ? editForm.expiry_date.toISOString() : undefined,
            };

            await apiService.updateUser(editingUser.id, userUpdatePayload);

            const targetOrgTier = editForm.product_plan === ProductPlan.TEAM_PLAN ? 'GROWTH' : 'DEFAULT';
            if (targetOrgTier !== editingUser.plan_tier || editForm.plan_tier !== editingUser.plan_tier) {
                const finalTier = editForm.plan_tier || targetOrgTier;
                await apiService.upgradeOrganizationTier(editingUser.id, finalTier);
            }

            setEditingUser(null);
            setTimeout(() => loadAdminData(), 200); 
        } catch (error: any) {
            const msg = error.response?.data?.detail || t('common.error_occurred');
            alert(msg);
        }
    };

    const handleDeleteUser = async (userId: string) => {
        if (!window.confirm(t('admin.confirmDelete', 'A jeni të sigurt?'))) return;
        try {
            await apiService.deleteUser(userId);
            loadAdminData();
        } catch (error) {
            console.error("Failed to delete user", error);
        }
    };

    const renderStatusBadge = (user: UnifiedAdminUser) => {
        const isExpired = user.expiry_date && user.expiry_date < new Date();

        if (user.status === 'pending_invite') {
            return (
                <span className="flex items-center text-warning-start bg-warning-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-warning-start/20 shadow-sm">
                    <Mail className="w-3.5 h-3.5 mr-1" /> {t('admin.status.invite_pending', 'FTESË')}
                </span>
            );
        }

        if (user.subscription_status === 'INACTIVE' || user.status === 'inactive') {
            return (
                <span className="flex items-center text-danger-start bg-danger-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-danger-start/20 shadow-sm">
                    <ShieldAlert className="w-3.5 h-3.5 mr-1" /> {t('admin.status.inactive', 'INAKTIV')}
                </span>
            );
        }

        if (user.subscription_status === 'ACTIVE') {
            if (isExpired) {
                return (
                    <span className="flex items-center text-danger-start bg-danger-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-danger-start/20 shadow-sm">
                        <AlertTriangle className="w-3.5 h-3.5 mr-1" /> {t('admin.status.expired', 'SKADUAR')}
                    </span>
                );
            }
            return (
                <span className="flex items-center text-success-start bg-success-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-success-start/20 shadow-sm">
                    <CheckCircle className="w-3.5 h-3.5 mr-1" /> {t('admin.status.active', 'AKTIV')}
                </span>
            );
        }

        return (
            <span className="flex items-center text-warning-start bg-warning-start/10 px-2.5 py-1 rounded-lg text-xs font-bold w-fit border border-warning-start/20 shadow-sm">
                <Clock className="w-3.5 h-3.5 mr-1" /> {t('admin.status.pending', 'PRITJE')}
            </span>
        );
    };

    // Filter Cases
    const filteredCases = cases.filter(c => {
        const matchesSearch = 
            c.title?.toLowerCase().includes(caseSearchQuery.toLowerCase()) ||
            c.client_name?.toLowerCase().includes(caseSearchQuery.toLowerCase()) ||
            c.owner_email?.toLowerCase().includes(caseSearchQuery.toLowerCase());

        if (!matchesSearch) return false;

        if (caseFilter === 'LOCKED') return !c.is_unlocked;
        if (caseFilter === 'UNLOCKED') return c.is_unlocked;
        return true;
    });

    const totalRevenueEst = cases.reduce((acc, c) => acc + (c.is_unlocked ? (c.unlock_amount || 9.99) : 0), 0);

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-canvas">
            <style>{`.dark-select { color-scheme: dark; } .react-datepicker-wrapper { width: 100%; }`}</style>
            
            {/* Header */}
            <div className="mb-6 select-none flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-black text-text-primary mb-1">Paneli i Super Adminit</h1>
                    <p className="text-text-secondary text-sm">Menaxhimi i Pagesave, Zhbllokimi me 1 Klikim dhe Kontrolli i Përdoruesve</p>
                </div>
                <button 
                    onClick={() => { loadCasesData(); loadAdminData(); }}
                    className="flex items-center gap-2 px-4 py-2 bg-surface hover:bg-hover border border-main rounded-xl text-xs font-bold text-text-primary transition-all w-fit shadow-sm"
                >
                    <RefreshCw className={`w-3.5 h-3.5 ${(isLoadingCases || isLoadingUsers) ? 'animate-spin' : ''}`} /> Rifresko të Dhënat
                </button>
            </div>

            {/* Main Tabs Navigation */}
            <div className="flex items-center gap-3 mb-6 border-b border-main pb-2">
                <button
                    onClick={() => setActiveTab('CASES_PAYMENTS')}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm transition-all ${
                        activeTab === 'CASES_PAYMENTS'
                            ? 'bg-primary-start text-white shadow-lg shadow-primary-start/20'
                            : 'bg-surface text-text-secondary hover:text-text-primary border border-main'
                    }`}
                >
                    <DollarSign className="w-4 h-4" /> 💰 Lëndët & Pagesat (Zhbllokim me 1 Klikim)
                </button>
                <button
                    onClick={() => setActiveTab('USERS')}
                    className={`flex items-center gap-2 px-5 py-3 rounded-xl font-bold text-sm transition-all ${
                        activeTab === 'USERS'
                            ? 'bg-primary-start text-white shadow-lg shadow-primary-start/20'
                            : 'bg-surface text-text-secondary hover:text-text-primary border border-main'
                    }`}
                >
                    <UserIcon className="w-4 h-4" /> 👥 Baza e Përdoruesve ({users.length})
                </button>
            </div>

            {/* ========================================================================= */}
            {/* TAB 1: 💰 LËNDËT DHE PAGESAT ME 1 KLIKIM */}
            {/* ========================================================================= */}
            {activeTab === 'CASES_PAYMENTS' && (
                <div className="space-y-6">
                    {/* Quick Stats Grid */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="glass-panel p-4 rounded-2xl border border-main bg-surface/40">
                            <div className="text-text-muted text-xs font-bold uppercase mb-1">Gjithsej Lëndë</div>
                            <div className="text-2xl font-black text-text-primary">{cases.length}</div>
                        </div>
                        <div className="glass-panel p-4 rounded-2xl border border-success-start/20 bg-success-start/5">
                            <div className="text-success-start text-xs font-bold uppercase mb-1">Të Zhbllokuara</div>
                            <div className="text-2xl font-black text-success-start">{cases.filter(c => c.is_unlocked).length}</div>
                        </div>
                        <div className="glass-panel p-4 rounded-2xl border border-warning-start/20 bg-warning-start/5">
                            <div className="text-warning-start text-xs font-bold uppercase mb-1">Në Pritje Pagese</div>
                            <div className="text-2xl font-black text-warning-start">{cases.filter(c => !c.is_unlocked).length}</div>
                        </div>
                        <div className="glass-panel p-4 rounded-2xl border border-primary-start/20 bg-primary-start/5">
                            <div className="text-primary-start text-xs font-bold uppercase mb-1">Fitimi Total i Vlerësuar</div>
                            <div className="text-2xl font-black text-primary-start">{totalRevenueEst.toFixed(2)} €</div>
                        </div>
                    </div>

                    {/* Table Container */}
                    <div className="glass-panel rounded-2xl border border-main overflow-hidden bg-canvas">
                        {/* Search & Filters */}
                        <div className="p-4 border-b border-main flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-surface">
                            <div className="flex items-center gap-2 select-none">
                                <FolderGit2 className="w-5 h-5 text-primary-start" />
                                <h3 className="text-base font-bold text-text-primary">Menaxhimi i Zhbllokimit të Lëndëve</h3>
                            </div>
                            <div className="relative w-full sm:w-72 flex items-center">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                                <input 
                                    type="text" 
                                    placeholder="Kërko lëndën, klientin, email-in..." 
                                    value={caseSearchQuery} 
                                    onChange={(e) => setCaseSearchQuery(e.target.value)} 
                                    className="w-full h-10 pl-9 pr-4 bg-canvas border border-main rounded-xl text-sm text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
                                />
                            </div>
                        </div>

                        {/* Filter Pills */}
                        <div className="p-3 border-b border-main bg-canvas/40 flex flex-wrap items-center gap-2 select-none">
                            <button
                                onClick={() => setCaseFilter('ALL')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                                    caseFilter === 'ALL' ? 'bg-primary-start text-white' : 'bg-surface text-text-secondary border border-main'
                                }`}
                            >
                                Të Gjitha ({cases.length})
                            </button>
                            <button
                                onClick={() => setCaseFilter('LOCKED')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                                    caseFilter === 'LOCKED' ? 'bg-warning-start text-white' : 'bg-surface text-text-secondary border border-main'
                                }`}
                            >
                                <Lock className="w-3 h-3" /> Të Bllokuara ({cases.filter(c => !c.is_unlocked).length})
                            </button>
                            <button
                                onClick={() => setCaseFilter('UNLOCKED')}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                                    caseFilter === 'UNLOCKED' ? 'bg-success-start text-white' : 'bg-surface text-text-secondary border border-main'
                                }`}
                            >
                                <Unlock className="w-3 h-3" /> Të Zhbllokuara ({cases.filter(c => c.is_unlocked).length})
                            </button>
                        </div>

                        {/* Desktop Table */}
                        <div className="w-full overflow-x-auto">
                            <table className="w-full text-left text-sm text-text-secondary">
                                <thead className="bg-surface text-text-primary uppercase text-xs font-bold border-b border-main select-none">
                                    <tr>
                                        <th className="px-6 py-4">Titulli i Lëndës & Klienti</th>
                                        <th className="px-6 py-4">Përdoruesi (Pronari)</th>
                                        <th className="px-6 py-4 text-center">Dokumente</th>
                                        <th className="px-6 py-4">Statusi i Pagesës</th>
                                        <th className="px-6 py-4 text-right">Veprimi me 1 Klikim</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-main">
                                    {isLoadingCases ? (
                                        <tr>
                                            <td colSpan={5} className="py-12 text-center text-text-secondary">
                                                <Loader2 className="animate-spin h-6 w-6 text-primary-start mx-auto" />
                                            </td>
                                        </tr>
                                    ) : filteredCases.length === 0 ? (
                                        <tr>
                                            <td colSpan={5} className="py-12 text-center text-text-secondary italic text-sm font-medium">
                                                Asnjë lëndë nuk u gjet.
                                            </td>
                                        </tr>
                                    ) : (
                                        filteredCases.map((c) => (
                                            <tr key={c._id} className="hover:bg-hover transition-colors">
                                                <td className="px-6 py-4">
                                                    <div className="font-bold text-text-primary text-base">{c.title}</div>
                                                    <div className="text-xs text-text-muted mt-0.5">
                                                        Klienti: <span className="font-semibold text-text-secondary">{c.client_name}</span> ({c.client_position})
                                                    </div>
                                                </td>
                                                <td className="px-6 py-4">
                                                    <div className="font-semibold text-text-primary">{c.owner_name || 'Përdorues'}</div>
                                                    <div className="text-xs text-text-muted">{c.owner_email}</div>
                                                </td>
                                                <td className="px-6 py-4 text-center">
                                                    <span className="px-2.5 py-1 bg-surface border border-main rounded-lg text-xs font-bold text-text-primary">
                                                        {c.document_count || 0} Faqe/Akte
                                                    </span>
                                                </td>
                                                <td className="px-6 py-4">
                                                    {c.is_unlocked ? (
                                                        <div className="space-y-0.5">
                                                            <span className="inline-flex items-center gap-1 text-success-start bg-success-start/10 px-2.5 py-1 rounded-lg text-xs font-bold border border-success-start/20 shadow-sm">
                                                                <CheckCircle className="w-3.5 h-3.5" /> E ZHBLLOKUAR (AKTIVE)
                                                            </span>
                                                            <div className="text-[11px] text-text-muted font-mono">
                                                                {c.unlock_payment_method || 'CASH'} • {c.unlock_amount || 9.99}€
                                                            </div>
                                                        </div>
                                                    ) : (
                                                        <span className="inline-flex items-center gap-1 text-warning-start bg-warning-start/10 px-2.5 py-1 rounded-lg text-xs font-bold border border-warning-start/20 shadow-sm">
                                                            <Lock className="w-3.5 h-3.5" /> E BLLOKUAR (PRET PAGESË)
                                                        </span>
                                                    )}
                                                </td>
                                                <td className="px-6 py-4 text-right">
                                                    {c.is_unlocked ? (
                                                        <button
                                                            onClick={() => handleLockCase(c._id)}
                                                            disabled={actionLoadingId === c._id}
                                                            className="px-3 py-1.5 bg-danger-start/10 text-danger-start hover:bg-danger-start/20 border border-danger-start/20 rounded-lg text-xs font-bold transition-all inline-flex items-center gap-1.5 focus:outline-none"
                                                        >
                                                            <Lock className="w-3.5 h-3.5" /> Blloko
                                                        </button>
                                                    ) : (
                                                        <div className="inline-flex items-center gap-2">
                                                            <button
                                                                onClick={() => handleUnlockCase(c._id, 'CASH', 9.99)}
                                                                disabled={actionLoadingId === c._id}
                                                                className="px-3 py-1.5 bg-success-start text-white hover:bg-opacity-90 rounded-lg text-xs font-bold shadow-md shadow-success-start/20 transition-all inline-flex items-center gap-1.5 focus:outline-none"
                                                            >
                                                                {actionLoadingId === c._id ? (
                                                                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                                                ) : (
                                                                    <Banknote className="w-3.5 h-3.5" />
                                                                )}
                                                                🔓 Zhblloko (Cash 10€)
                                                            </button>
                                                            <button
                                                                onClick={() => handleUnlockCase(c._id, 'MBANKING', 9.99)}
                                                                disabled={actionLoadingId === c._id}
                                                                className="px-2.5 py-1.5 bg-surface text-primary-start hover:bg-hover border border-primary-start/30 rounded-lg text-xs font-bold transition-all inline-flex items-center gap-1 focus:outline-none"
                                                                title="Zhblloko si m-Banking"
                                                            >
                                                                <CreditCard className="w-3.5 h-3.5" /> m-Bank
                                                            </button>
                                                        </div>
                                                    )}
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 2: 👥 BAZA E PËRDORUESVE (ORIGJINALE E RUAJTUR 100%) */}
            {/* ========================================================================= */}
            {activeTab === 'USERS' && (
                <div className="glass-panel rounded-2xl border border-main overflow-hidden bg-canvas">
                    {/* Search & Header Row */}
                    <div className="p-4 border-b border-main flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-surface">
                        <div className="flex items-center gap-2 select-none h-11 sm:h-auto">
                            <Briefcase className="w-5 h-5 text-primary-start" />
                            <h3 className="text-base sm:text-lg font-bold text-text-primary">{t('admin.user_base_title', 'Baza e Përdoruesve')}</h3>
                        </div>
                        <div className="relative w-full sm:w-64 h-11 flex items-center">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-muted" />
                            <input 
                                type="text" 
                                placeholder={t('general.search_placeholder', 'Kërko...')} 
                                value={searchQuery} 
                                onChange={(e) => setSearchQuery(e.target.value)} 
                                className="w-full h-11 sm:h-9 pl-9 pr-4 bg-canvas border border-main rounded-xl text-sm text-text-primary placeholder:text-text-disabled focus:outline-none focus:ring-2 focus:ring-primary-start/20 transition-all"
                            />
                        </div>
                    </div>

                    {/* Interactive Status Filter Pills */}
                    <div className="p-3 border-b border-main bg-canvas/40 flex flex-wrap items-center gap-2 select-none">
                        <div className="flex items-center gap-1 text-xs font-bold text-text-muted mr-1">
                            <Filter className="w-3.5 h-3.5 text-primary-start" /> Filterat:
                        </div>
                        {[
                            { key: 'ALL', label: 'Të Gjithë', count: users.length },
                            { 
                                key: 'ACTIVE', 
                                label: 'Aktivë', 
                                count: users.filter(u => u.status === 'active' && u.subscription_status === 'ACTIVE' && (!u.expiry_date || u.expiry_date >= new Date())).length 
                            },
                            { 
                                key: 'PENDING', 
                                label: 'Ftesa', 
                                count: users.filter(u => u.status === 'pending_invite').length 
                            },
                            { 
                                key: 'INACTIVE_EXPIRED', 
                                label: 'Inaktivë / Skaduar', 
                                count: users.filter(u => u.subscription_status === 'INACTIVE' || u.status === 'inactive' || (u.expiry_date && u.expiry_date < new Date())).length 
                            },
                            { 
                                key: 'TEAM', 
                                label: 'TEAM (5 Vende)', 
                                count: users.filter(u => u.product_plan === ProductPlan.TEAM_PLAN).length 
                            },
                        ].map(f => (
                            <button
                                key={f.key}
                                type="button"
                                onClick={() => setStatusFilter(f.key as StatusFilter)}
                                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 focus:outline-none ${
                                    statusFilter === f.key 
                                        ? 'bg-primary-start text-white shadow-md shadow-primary-start/20' 
                                        : 'bg-surface hover:bg-hover text-text-secondary border border-main'
                                }`}
                            >
                                <span>{f.label}</span>
                                <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-black ${
                                    statusFilter === f.key ? 'bg-white/20 text-white' : 'bg-canvas text-text-muted'
                                }`}>
                                    {f.count}
                                </span>
                            </button>
                        ))}
                    </div>

                    {/* Desktop view standard data table */}
                    <div className="w-full overflow-x-auto">
                        <table className="w-full text-left text-sm text-text-secondary">
                            <thead className="bg-surface text-text-primary uppercase text-xs font-bold border-b border-main select-none">
                                <tr>
                                    <th className="px-6 py-4">{t('admin.table.user', 'Përdoruesi')}</th>
                                    <th className="px-6 py-4 text-center">{t('admin.table.plan_type', 'Tipi')}</th>
                                    <th className="px-6 py-4">{t('admin.table.capacity', 'Plani & Kapaciteti')}</th>
                                    <th className="px-6 py-4">{t('admin.table.start_date', 'Koha e Regjistrimit')}</th>
                                    <th className="px-6 py-4">{t('admin.table.expiry_date', 'Skadimi i Planit')}</th>
                                    <th className="px-6 py-4">{t('admin.table.status', 'Statusi')}</th>
                                    <th className="px-6 py-4 text-right">{t('admin.table.actions', 'Veprime')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-main">
                                {users.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="py-12 text-center text-text-secondary italic text-sm font-medium">
                                            Asnjë përdorues nuk u gjet.
                                        </td>
                                    </tr>
                                ) : (
                                    users.map((user) => (
                                        <tr key={user.id} className="hover:bg-hover transition-colors">
                                            <td className="px-6 py-4">
                                                <div className="font-bold text-text-primary">{user.username}</div>
                                                <div className="text-xs text-text-muted">{user.email}</div>
                                            </td>
                                            <td className="px-6 py-4 text-center">
                                                {user.account_type === AccountType.ORGANIZATION ? <Building2 className="w-4 h-4 text-secondary-start mx-auto" /> : <UserIcon className="w-4 h-4 text-text-muted mx-auto" />}
                                            </td>
                                            <td className="px-6 py-4">
                                                <div className="flex items-center gap-2">
                                                    {user.product_plan === ProductPlan.TEAM_PLAN ? <Star className="w-3 h-3 text-warning-start animate-pulse" /> : <UserIcon className="w-3 h-3 text-text-muted" />}
                                                    <span className={`text-xs font-bold ${user.product_plan === ProductPlan.TEAM_PLAN ? 'text-warning-start' : 'text-text-muted'}`}>
                                                        {user.product_plan} ({user.user_limit} {t('admin.seats', 'Vende')})
                                                    </span>
                                                </div>
                                            </td>
                                            <td className="px-6 py-4 font-mono text-xs select-none">
                                                {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                                            </td>
                                            <td className="px-6 py-4 font-mono text-xs select-none">
                                                {user.expiry_date ? user.expiry_date.toLocaleDateString() : (
                                                    <span className="text-text-muted italic">Pa Skadim</span>
                                                )}
                                            </td>
                                            <td className="px-6 py-4">{renderStatusBadge(user)}</td>
                                            <td className="px-6 py-4 text-right space-x-2 whitespace-nowrap">
                                                <button 
                                                    type="button"
                                                    onClick={() => handleEditClick(user)} 
                                                    className="p-2 bg-primary-start/10 text-primary-start rounded-lg border border-primary-start/20 hover:bg-primary-start/20 transition-colors focus:outline-none"
                                                >
                                                    <Edit2 className="w-4 h-4" />
                                                </button>
                                                <button 
                                                    type="button"
                                                    onClick={() => handleDeleteUser(user.id)} 
                                                    className="p-2 bg-danger-start/10 text-danger-start rounded-lg border border-danger-start/20 hover:bg-danger-start/20 transition-colors focus:outline-none"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Editing SaaS Profile Modal */}
            {editingUser && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 overflow-y-auto custom-finance-scroll">
                    <motion.div 
                        initial={{ scale: 0.95, opacity: 0 }} 
                        animate={{ scale: 1, opacity: 1 }} 
                        className="glass-panel border border-main p-6 rounded-2xl w-full max-w-lg shadow-2xl overflow-y-auto max-h-[90vh] bg-canvas"
                    >
                        <h3 className="text-xl font-bold text-text-primary mb-6 border-b border-main pb-4 tracking-tight select-none">
                            {t('admin.manage_saas_profile', 'Menaxho Profilin SaaS')}: {editingUser.username}
                        </h3>
                        <form onSubmit={handleUpdateUser} className="space-y-6">
                            
                            {/* Role Management Section */}
                            <div className="p-4 bg-primary-start/5 rounded-xl border border-primary-start/20 space-y-4">
                                <h4 className="text-xs font-bold text-primary-start uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Key size={14} /> {t('admin.section_role', 'Roli i Përdoruesit')}
                                </h4>
                                <div className="space-y-1.5">
                                    <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                        {t('admin.label_role', 'Roli')}
                                    </label>
                                    <select 
                                        value={editForm.role || 'STANDARD'} 
                                        onChange={e => setEditForm({ 
                                            ...editForm, 
                                            role: e.target.value as UserRole
                                        })} 
                                        className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                    >
                                        <option value="STANDARD" className="bg-canvas text-text-primary">{t('admin.option_role_standard', 'STANDARD (Përdorues i zakonshëm)')}</option>
                                        <option value="ADMIN" className="bg-canvas text-text-primary">{t('admin.option_role_admin', 'ADMIN (Administrator)')}</option>
                                    </select>
                                </div>
                            </div>

                            {/* Capacity and Quota Management Section */}
                            <div className="p-4 bg-status-success/5 rounded-xl border border-status-success/20 space-y-4">
                                <h4 className="text-xs font-bold text-status-success uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Star size={14} /> {t('admin.section_capacity_quotas', 'Kapaciteti & Kuotat')}
                                </h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_product_plan', 'Plani i Produktit')}
                                        </label>
                                        <select 
                                            value={editForm.product_plan} 
                                            onChange={e => setEditForm({ ...editForm, product_plan: e.target.value as ProductPlan })} 
                                            className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value={ProductPlan.SOLO_PLAN} className="bg-canvas text-text-primary">{t('admin.option_plan_solo', 'SOLO (1 Vend)')}</option>
                                            <option value={ProductPlan.TEAM_PLAN} className="bg-canvas text-text-primary">{t('admin.option_plan_team', 'TEAM (5 Vende)')}</option>
                                        </select>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_account_type', 'Tipi i Llogarisë')}
                                        </label>
                                        <select 
                                            value={editForm.account_type} 
                                            onChange={e => setEditForm({ ...editForm, account_type: e.target.value as AccountType })} 
                                            className="w-full rounded-xl px-3 h-11 bg-surface border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value={AccountType.SOLO} className="bg-canvas text-text-primary">{t('admin.option_account_individual', 'Individual')}</option>
                                            <option value={AccountType.ORGANIZATION} className="bg-canvas text-text-primary">{t('admin.option_account_organization', 'Firmë/Organizatë')}</option>
                                        </select>
                                    </div>
                                </div>
                            </div>

                            {/* Lifecycle and Status Section */}
                            <div className="p-4 bg-surface border border-main space-y-4 rounded-xl">
                                <h4 className="text-xs font-bold text-primary-start uppercase tracking-widest flex items-center gap-2 select-none">
                                    <Clock size={14} /> {t('admin.section_lifecycle_status', 'Cikli i Jetës & Statusi')}
                                </h4>
                                <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_gatekeeper_status', 'Statusi i Gatekeeper')}
                                        </label>
                                        <select 
                                            value={editForm.subscription_status} 
                                            onChange={e => setEditForm({ ...editForm, subscription_status: e.target.value })} 
                                            className="w-full rounded-xl px-3 h-11 bg-canvas border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value="ACTIVE" className="bg-canvas text-text-primary">{t('admin.option_status_active', 'ACTIVE (Akses i Lejuar)')}</option>
                                            <option value="INACTIVE" className="bg-canvas text-text-primary">{t('admin.option_status_inactive', 'INACTIVE (Akses i Refuzuar)')}</option>
                                        </select>
                                    </div>
                                    
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            Statusi i Llogarisë
                                        </label>
                                        <select 
                                            value={editForm.status || 'active'} 
                                            onChange={e => setEditForm({ ...editForm, status: e.target.value as 'active' | 'inactive' | 'pending_invite' })} 
                                            className="w-full rounded-xl px-3 h-11 bg-canvas border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20"
                                        >
                                            <option value="active" className="bg-canvas text-text-primary">AKTIV (Llogari e Aktivizuar)</option>
                                            <option value="pending_invite" className="bg-canvas text-text-primary">FTESË (Në pritje të pranimit)</option>
                                            <option value="inactive" className="bg-canvas text-text-primary">INAKTIV (Llogari e Deaktivizuar)</option>
                                        </select>
                                    </div>
                                </div>
                                
                                <div className="grid grid-cols-1 gap-4">
                                    <div className="space-y-1.5">
                                        <label className="block text-[10px] font-bold text-text-secondary uppercase mb-1">
                                            {t('admin.label_expiry_date', 'Data e Skadimit')}
                                        </label>
                                        <DatePicker 
                                            selected={editForm.expiry_date} 
                                            onChange={(date) => setEditForm({ ...editForm, expiry_date: date })} 
                                            className="w-full rounded-xl px-3 h-11 bg-canvas border border-main text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-start/20" 
                                            placeholderText={t('admin.placeholder_no_expiry', 'Pa Skadim')} 
                                            dateFormat="dd/MM/yyyy" 
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-6 border-t border-main">
                                <button 
                                    type="button" 
                                    onClick={() => setEditingUser(null)} 
                                    className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-hover border border-main transition-all focus:outline-none"
                                >
                                    {t('general.cancel', 'Anulo')}
                                </button>
                                <button 
                                    type="submit" 
                                    className="w-full sm:w-auto px-6 h-11 rounded-xl text-sm font-bold bg-primary-start hover:bg-opacity-95 text-white shadow-lg shadow-primary-start/15 focus:outline-none"
                                >
                                    {t('admin.button_save_profile', 'Ruaj Profilin SaaS')}
                                </button>
                            </div>
                        </form>
                    </motion.div>
                </div>
            )}
        </div>
    );
};

export default AdminDashboardPage;