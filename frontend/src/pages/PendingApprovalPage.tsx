// FILE: src/pages/PendingApprovalPage.tsx
// PHOENIX PROTOCOL - PENDING APPROVAL V1.0
// Faqe për user me subscription_status != 'ACTIVE' ose abonim të skaduar.
// Shfaqet pas login-it, përpara se të hyjë në dashboard.
// Whitelist: butonat për Suport + Logout + shikim i statusit.

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { motion } from 'framer-motion';
import { Clock, Mail, LogOut, ShieldAlert, CheckCircle2 } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

const PendingApprovalPage: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const isExpired = user?.subscription_expiry
    ? new Date(user.subscription_expiry) < new Date()
    : false;

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-canvas px-4 font-sans selection:bg-primary-start/30">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="glass-panel max-w-lg w-full p-8 sm:p-10 rounded-3xl border border-main shadow-2xl"
      >
        {/* Brand */}
        <div className="flex justify-center mb-8">
          <BrandLogo />
        </div>

        {/* Status Icon */}
        <div className="flex justify-center mb-6">
          {isExpired ? (
            <div className="w-20 h-20 rounded-full bg-danger-start/10 border-2 border-danger-start/30 flex items-center justify-center">
              <ShieldAlert className="w-10 h-10 text-danger-start" />
            </div>
          ) : (
            <div className="w-20 h-20 rounded-full bg-warning-start/10 border-2 border-warning-start/30 flex items-center justify-center animate-pulse">
              <Clock className="w-10 h-10 text-warning-start" />
            </div>
          )}
        </div>

        {/* Title */}
        <div className="text-center space-y-3 mb-8">
          <h1 className="text-2xl sm:text-3xl font-black text-text-primary tracking-tight">
            {isExpired
              ? 'Abonimi juaj ka skaduar'
              : 'Llogaria juaj është në shqyrtim'}
          </h1>
          <p className="text-sm text-text-secondary leading-relaxed">
            {isExpired
              ? 'Për të vazhduar përdorimin e platformës, ju lutem renovoni planin tuaj duke kontaktuar ekipin e Juristi.tech.'
              : 'Faleminderit që u regjistruat në Juristi.tech. Ekipi ynë po shqyrton kërkesën tuaj për aktivizim. Do t\'ju kontaktojmë brenda 24 orëve.'}
          </p>
        </div>

        {/* User Info */}
        {user && (
          <div className="mb-8 p-4 rounded-2xl bg-surface/60 border border-main space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-muted font-semibold uppercase tracking-wider">Llogaria</span>
              <span className="text-text-primary font-mono">{user.email}</span>
            </div>
            {user.username && (
              <div className="flex items-center justify-between text-xs">
                <span className="text-text-muted font-semibold uppercase tracking-wider">Përdoruesi</span>
                <span className="text-text-primary font-mono">{user.username}</span>
              </div>
            )}
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-muted font-semibold uppercase tracking-wider">Statusi</span>
              <span className={`font-bold uppercase tracking-wider ${
                isExpired ? 'text-danger-start' : 'text-warning-start'
              }`}>
                {isExpired ? 'Skaduar' : (user.subscription_status || 'INAKTIV')}
              </span>
            </div>
          </div>
        )}

        {/* Next Steps */}
        <div className="mb-8 p-4 rounded-2xl bg-primary-start/5 border border-primary-start/20 space-y-3">
          <h3 className="text-xs font-bold text-primary-start uppercase tracking-widest flex items-center gap-2">
            <CheckCircle2 size={14} /> Hapat e mëtejshëm
          </h3>
          <ul className="text-xs text-text-secondary space-y-1.5 leading-relaxed">
            <li>1. Ekipi i Juristi.tech verifikon të dhënat tuaja</li>
            <li>2. Ju njoftojmë me email sapo llogaria aktivizohet</li>
            <li>3. Pas aktivizimit, mund të hyni dhe të përdorni të gjitha veçoritë</li>
          </ul>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={() => navigate('/support')}
            className="flex-1 h-12 px-6 rounded-xl bg-primary-start hover:bg-primary-start/90 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-primary-start/20 transition-all active:scale-[0.98] cursor-pointer"
          >
            <Mail size={16} />
            Kontakto Suportin
          </button>
          <button
            onClick={handleLogout}
            className="flex-1 h-12 px-6 rounded-xl bg-surface hover:bg-hover border border-main text-text-primary font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all active:scale-[0.98] cursor-pointer"
          >
            <LogOut size={16} />
            Shkëputu
          </button>
        </div>

        {/* Footer */}
        <div className="mt-8 pt-6 border-t border-main text-center text-[10px] text-text-muted uppercase tracking-widest">
          Juristi AI / Advocatus — Prishtinë, Kosovë
        </div>
      </motion.div>
    </div>
  );
};

export default PendingApprovalPage;