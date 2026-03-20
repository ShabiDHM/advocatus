// FILE: src/pages/SupportPage.tsx
// PHOENIX PROTOCOL - SUPPORT PAGE V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Semantic classes: glass-panel, glass-input, btn-primary, text-text-primary, text-text-secondary, border-main.
// 2. Consistent with LoginPage and RegisterPage styling.
// 3. Preserved all form logic and PrivacyModal.

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Phone, MapPin, Send, Loader2, Lock, Mail } from 'lucide-react';
import { apiService } from '../services/api';
import PrivacyModal from '../components/PrivacyModal';

const SupportPage: React.FC = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({ firstName: '', lastName: '', email: '', phone: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await apiService.sendContactForm(formData);
      alert(t('support.successMessage', 'Mesazhi u dërgua me sukses!'));
      setFormData({ firstName: '', lastName: '', email: '', phone: '', message: '' });
    } catch (error) {
      console.error(error);
      alert(t('error.generic'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 h-full">
        <h1 className="text-3xl font-semibold text-text-primary mb-8">{t('support.title', 'Qendra e Ndihmës')}</h1>
        
        {/* Main Grid: items-stretch ensures both columns have the same height */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-stretch">
          
          {/* Left Column: Flex container ensures cards fill the vertical space */}
          <div className="flex flex-col gap-6 h-full">
            
            {/* Card 1: Contact Info */}
            <div className="glass-panel p-6 rounded-2xl border border-main">
              <h3 className="text-xl font-semibold mb-4 text-text-primary">{t('support.contactInfo', 'Informacion Kontakti')}</h3>
              <div className="space-y-4 text-text-secondary">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary-start/10 text-primary-start">
                    <Phone size={20} />
                  </div> 
                  <span className="font-medium">+383 44 987 898</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary-start/10 text-primary-start">
                    <Mail size={20} />
                  </div> 
                  <span className="font-medium">info@juristi.tech</span>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-primary-start/10 text-primary-start">
                    <MapPin size={20} />
                  </div>
                  <span className="font-medium">Xhavit Haziri 10, 10000 Prishtinë</span>
                </div>
              </div>
            </div>

            {/* Card 2: Legal Info (Expands to fill remaining height) */}
            <div className="glass-panel p-6 rounded-2xl border border-main flex-1 flex flex-col justify-center">
              <div>
                <h3 className="text-xl font-semibold mb-4 text-text-primary">{t('support.legalInfo', 'Informacione Ligjore')}</h3>
                <p className="text-text-secondary text-sm mb-6 leading-relaxed">
                  {t('support.legalDesc', 'Lexoni politikën tonë të privatësisë për të kuptuar se si i mbrojmë të dhënat tuaja dhe të drejtat tuaja ligjore.')}
                </p>
              </div>
              <button 
                onClick={() => setIsPrivacyOpen(true)}
                className="w-full flex justify-center items-center py-3 rounded-xl bg-primary-start/10 text-primary-start font-semibold hover:bg-primary-start/20 border border-primary-start/20 transition-all active:scale-95"
              >
                <Lock className="mr-2 h-4 w-4" /> {t('support.privacyTitle', 'Politika e Privatësisë')}
              </button>
            </div>
          </div>

          {/* Right Column: Form */}
          <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-main h-full flex flex-col justify-center">
            <h3 className="text-xl font-semibold mb-6 text-text-primary">{t('support.sendMessage', 'Na Dërgoni Mesazh')}</h3>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">{t('auth.firstName', 'Emri')}</label>
                  <input type="text" required value={formData.firstName} onChange={e => setFormData({...formData, firstName: e.target.value})} className="glass-input w-full rounded-xl px-4 py-3 border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">{t('auth.lastName', 'Mbiemri')}</label>
                  <input type="text" required value={formData.lastName} onChange={e => setFormData({...formData, lastName: e.target.value})} className="glass-input w-full rounded-xl px-4 py-3 border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all" />
                </div>
              </div>
              
              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">{t('auth.email', 'Email')}</label>
                <input type="email" required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="glass-input w-full rounded-xl px-4 py-3 border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all" />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold uppercase tracking-wider text-text-secondary ml-1">{t('support.messageLabel', 'Mesazhi')}</label>
                <textarea required rows={5} value={formData.message} onChange={e => setFormData({...formData, message: e.target.value})} className="glass-input w-full rounded-xl px-4 py-3 border border-main bg-surface focus:border-primary-start focus:ring-1 focus:ring-primary-start/40 transition-all resize-none" />
              </div>
              
              <button type="submit" disabled={isSubmitting} className="btn-primary w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 shadow-lg hover:shadow-primary-start/20 transition-all active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-2">
                {isSubmitting ? <Loader2 className="animate-spin" /> : <><Send className="mr-2 h-4 w-4" /> {t('support.sendButton', 'Dërgo')}</>}
              </button>
            </form>
          </div>
        </div>
      </div>
      <PrivacyModal isOpen={isPrivacyOpen} onClose={() => setIsPrivacyOpen(false)} />
    </>
  );
};

export default SupportPage;