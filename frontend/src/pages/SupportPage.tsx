// FILE: src/pages/SupportPage.tsx
// PHOENIX PROTOCOL - BUILD FIX
// 1. INTEGRITY FIX: Removed the unused 'FileText' icon import from 'lucide-react' to resolve the TS6133 compilation error.
// 2. VERIFIED: All other functionality related to functionality consolidation remains intact.

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Mail, Phone, MapPin, Send, Loader2, Lock } from 'lucide-react';
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
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold text-text-primary mb-8">{t('support.title', 'Qendra e Ndihmës')}</h1>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column */}
          <div className="space-y-6">
            <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge">
              <h3 className="text-xl font-semibold mb-4 text-white">{t('support.contactInfo', 'Informacion Kontakti')}</h3>
              <div className="space-y-4 text-text-secondary">
                <div className="flex items-center gap-3"><Mail className="text-secondary-start" /> support@juristi.tech</div>
                <div className="flex items-center gap-3"><Phone className="text-secondary-start" /> +383 44 123 456</div>
                <div className="flex items-center gap-3"><MapPin className="text-secondary-start" /> Prishtinë, Kosovë</div>
              </div>
            </div>

            <div className="bg-background-light/30 p-6 rounded-2xl border border-glass-edge">
              <h3 className="text-xl font-semibold mb-4 text-white">{t('support.legalInfo', 'Informacione Ligjore')}</h3>
              <p className="text-text-secondary text-sm mb-4">{t('support.legalDesc', 'Lexoni politikën tonë të privatësisë për të kuptuar se si i mbrojmë të dhënat tuaja.')}</p>
              <button 
                onClick={() => setIsPrivacyOpen(true)}
                className="w-full flex justify-center items-center py-2.5 rounded-xl bg-secondary-start/10 text-secondary-start font-bold hover:bg-secondary-start/20 transition-all"
              >
                <Lock className="mr-2 h-4 w-4" /> {t('support.privacyTitle', 'Politika e Privatësisë')}
              </button>
            </div>
          </div>

          {/* Right Column: Form */}
          <div className="bg-background-light/30 p-6 sm:p-8 rounded-2xl border border-glass-edge">
            <h3 className="text-xl font-semibold mb-6 text-white">{t('support.sendMessage', 'Na Dërgoni Mesazh')}</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <input type="text" placeholder={t('auth.firstName', 'Emri')} required value={formData.firstName} onChange={e => setFormData({...formData, firstName: e.target.value})} className="bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
                <input type="text" placeholder={t('auth.lastName', 'Mbiemri')} required value={formData.lastName} onChange={e => setFormData({...formData, lastName: e.target.value})} className="bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
              </div>
              <input type="email" placeholder={t('auth.email', 'Email')} required value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
              <textarea placeholder={t('support.messagePlaceholder', 'Mesazhi juaj...')} required rows={4} value={formData.message} onChange={e => setFormData({...formData, message: e.target.value})} className="w-full bg-background-dark border border-glass-edge rounded-lg px-4 py-2 text-white focus:ring-1 focus:ring-primary-start outline-none" />
              
              <button type="submit" disabled={isSubmitting} className="w-full flex justify-center items-center py-2.5 rounded-xl bg-gradient-to-r from-primary-start to-primary-end text-white font-bold shadow-lg hover:opacity-90 disabled:opacity-50 transition-all">
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