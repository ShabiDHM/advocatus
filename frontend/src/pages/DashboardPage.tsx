// FILE: src/pages/DashboardPage.tsx
// PHOENIX PROTOCOL - CLEANUP
// 1. REMOVED: Hardcoded Footer (now handled by MainLayout).

import React, { useState, useEffect } from 'react';
import { Case, CreateCaseRequest } from '../data/types';
import { apiService } from '../services/api';
import CaseCard from '../components/CaseCard';
import { useTranslation } from 'react-i18next';
import { motion } from 'framer-motion'; 

const DashboardPage: React.FC = () => {
  const { t } = useTranslation();
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState('');
  const [newCaseClient, setNewCaseClient] = useState('');
  const [newCaseEmail, setNewCaseEmail] = useState('');
  const [newCasePhone, setNewCasePhone] = useState('');

  const fetchCases = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedCases = await apiService.getCases();
      setCases(fetchedCases);
    } catch (err: any) {
      console.error('[Dashboard] Fetch Error:', err);
      const status = err.response?.status;
      const url = err.config?.url;
      const fullUrl = err.config?.baseURL ? `${err.config.baseURL}${url}` : url;
      
      if (status === 404) {
        setError(`${t('dashboard.fetchCasesFailure')} (404 Not Found: ${fullUrl})`);
      } else {
        setError(t('dashboard.fetchCasesFailure')); 
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [t]);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseTitle || !newCaseClient) return;

    try {
      const requestData: CreateCaseRequest = {
        case_name: newCaseTitle, 
        clientName: newCaseClient,
        clientEmail: newCaseEmail,
        clientPhone: newCasePhone
      };

      const newCase = await apiService.createCase(requestData);

      setCases(prev => [newCase, ...prev]);
      setIsModalOpen(false);
      setNewCaseClient('');
      setNewCaseTitle('');
      setNewCaseEmail('');
      setNewCasePhone('');
    } catch (err) {
      setError(t('dashboard.createCaseFailure'));
      console.error(err);
    }
  };
  
  const handleDeleteCase = async (caseId: string) => {
      if (window.confirm(t('dashboard.confirmDeleteCase'))) {
          try {
              await apiService.deleteCase(caseId); 
              setCases(prev => prev.filter(c => c.id !== caseId));
          } catch (err) {
              setError(t('dashboard.deleteCaseFailure'));
              console.error(err);
          }
      }
  };

  return (
    <motion.div 
      className="dashboard-page flex flex-col h-full" 
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex-grow">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4 sm:gap-0">
          <h1 className="text-2xl sm:text-3xl font-extrabold text-text-primary">{t('general.dashboard')}</h1>
          <motion.button 
            onClick={() => setIsModalOpen(true)}
            className="w-full sm:w-auto text-white font-semibold py-3 sm:py-2 px-4 rounded-xl transition-all duration-300 shadow-lg glow-primary
                       bg-gradient-to-r from-primary-start to-primary-end flex justify-center items-center"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
          >
            + {t('dashboard.newCase')}
          </motion.button>
        </div>

        {isLoading && (
          <div className="text-text-secondary text-center py-10">
            <div className="spinner"></div>
            {t('dashboard.loadingCases')}
          </div>
        )}

        {error && (
          <div className="p-4 text-sm text-red-100 bg-red-700 rounded-lg mb-6 flex items-center gap-2">
            <span>{error}</span>
          </div>
        )}

        {/* Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 sm:gap-6 pb-6">
          {!isLoading && cases.length === 0 && !error && (
            <div className="col-span-full text-center py-10 text-text-secondary">
              {t('dashboard.noCasesFound')}
            </div>
          )}
          {cases.map((caseItem) => (
            <CaseCard key={caseItem.id} caseData={caseItem} onDelete={handleDeleteCase} />
          ))}
        </div>
      </div>

      {/* OLD FOOTER REMOVED HERE - NOW IN MAINLAYOUT */}

      {/* Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-background-dark bg-opacity-80 flex items-center justify-center z-50 p-4">
          <motion.form 
            onSubmit={handleCreateCase} 
            className="bg-background-light/70 backdrop-blur-md border border-glass-edge p-6 sm:p-8 rounded-2xl w-full max-w-lg shadow-2xl space-y-4"
            initial={{ opacity: 0, y: -50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 30 }}
          >
            <h2 className="text-xl font-bold text-text-primary">{t('dashboard.createCaseTitle')}</h2>
            <input
              type="text"
              placeholder={t('dashboard.caseTitlePlaceholder')}
              value={newCaseTitle}
              onChange={(e) => setNewCaseTitle(e.target.value)}
              className="w-full px-4 py-3 bg-background-dark/50 border border-glass-edge rounded-xl text-text-primary placeholder-text-secondary/50 focus:ring-primary-start focus:border-primary-start"
              required
            />
             <input
              type="text"
              placeholder={t('dashboard.clientNamePlaceholder')}
              value={newCaseClient}
              onChange={(e) => setNewCaseClient(e.target.value)}
              className="w-full px-4 py-3 bg-background-dark/50 border border-glass-edge rounded-xl text-text-primary placeholder-text-secondary/50 focus:ring-primary-start focus:border-primary-start"
              required
            />
            <input
              type="email"
              placeholder={t('dashboard.clientEmailPlaceholder')}
              value={newCaseEmail}
              onChange={(e) => setNewCaseEmail(e.target.value)}
              className="w-full px-4 py-3 bg-background-dark/50 border border-glass-edge rounded-xl text-text-primary placeholder-text-secondary/50 focus:ring-primary-start focus:border-primary-start"
            />
            <input
              type="tel"
              placeholder={t('dashboard.clientPhonePlaceholder')}
              value={newCasePhone}
              onChange={(e) => setNewCasePhone(e.target.value)}
              className="w-full px-4 py-3 bg-background-dark/50 border border-glass-edge rounded-xl text-text-primary placeholder-text-secondary/50 focus:ring-primary-start focus:border-primary-start"
            />
            
            <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-2">
              <motion.button 
                type="button" 
                onClick={() => setIsModalOpen(false)} 
                className="w-full sm:w-auto px-4 py-3 sm:py-2 rounded-xl text-text-secondary hover:text-text-primary bg-background-dark/50 border border-glass-edge transition-colors"
                whileHover={{ scale: 1.05 }}
              >
                {t('dashboard.cancelButton')}
              </motion.button>
              <motion.button 
                type="submit" 
                className="w-full sm:w-auto text-white font-semibold py-3 sm:py-2 px-4 rounded-xl transition-all duration-300 shadow-lg glow-primary
                           bg-gradient-to-r from-primary-start to-primary-end"
                whileHover={{ scale: 1.05 }}
              >
                {t('dashboard.createButton')}
              </motion.button>
            </div>
          </motion.form>
        </div>
      )}
    </motion.div>
  );
};

export default DashboardPage;