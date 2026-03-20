// FILE: src/components/ContactModal.tsx
// PHOENIX PROTOCOL - CONTACT MODAL V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary.
// 2. Button uses btn-primary class.
// 3. Preserved API integration and loading states.

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, CheckCircle, MessageSquare, User, Mail, Phone } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { apiService } from '../services/api';

interface ContactModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const ContactModal: React.FC<ContactModalProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({ 
    firstName: '', 
    lastName: '', 
    email: '', 
    phone: '', 
    message: '' 
  });
  const [isSending, setIsSending] = useState(false);
  const [isSent, setIsSent] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSending(true);
    
    try {
      await apiService.sendContactForm(formData);
      setIsSending(false);
      setIsSent(true);
      
      setTimeout(() => {
        setIsSent(false);
        setFormData({ firstName: '', lastName: '', email: '', phone: '', message: '' });
        onClose();
      }, 2000);
    } catch (error) {
      console.error("Failed to send contact form:", error);
      alert("Gabim gjatë dërgimit. Ju lutemi provoni përsëri.");
      setIsSending(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <motion.div 
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="glass-panel border border-main rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
      >
        <div className="p-5 border-b border-main flex justify-between items-center bg-surface/30">
          <h2 className="text-lg sm:text-xl font-bold text-text-primary flex items-center gap-2">
            <MessageSquare className="text-primary-start h-5 w-5" />
            {t('footer.contactSupport', 'Kontakto Mbështetjen')}
          </h2>
          <button onClick={onClose} className="text-text-secondary hover:text-text-primary transition-colors">
            <X size={24} />
          </button>
        </div>

        <div className="p-5 sm:p-6">
          <AnimatePresence mode='wait'>
            {isSent ? (
              <motion.div 
                initial={{ opacity: 0, y: 10 }} 
                animate={{ opacity: 1, y: 0 }}
                className="flex flex-col items-center justify-center py-8 text-center space-y-4"
              >
                <div className="h-16 w-16 bg-success-start/20 rounded-full flex items-center justify-center text-success-start">
                    <CheckCircle size={40} />
                </div>
                <h3 className="text-xl font-bold text-text-primary">Mesazhi u Dërgua!</h3>
                <p className="text-text-secondary">Ekipi ynë do t'ju kontaktojë së shpejti.</p>
              </motion.div>
            ) : (
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-text-secondary uppercase">Emri</label>
                        <div className="relative">
                            <User className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                            <input 
                                type="text" required 
                                value={formData.firstName}
                                onChange={e => setFormData({...formData, firstName: e.target.value})}
                                className="glass-input w-full pl-9 pr-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-primary-start outline-none transition-all"
                                placeholder="Emri juaj"
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-text-secondary uppercase">Mbiemri</label>
                        <input 
                            type="text" required
                            value={formData.lastName}
                            onChange={e => setFormData({...formData, lastName: e.target.value})}
                            className="glass-input w-full px-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-primary-start outline-none transition-all"
                            placeholder="Mbiemri"
                        />
                    </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-text-secondary uppercase">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                            <input 
                                type="email" required 
                                value={formData.email}
                                onChange={e => setFormData({...formData, email: e.target.value})}
                                className="glass-input w-full pl-9 pr-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-primary-start outline-none transition-all"
                                placeholder="email@shembull.com"
                            />
                        </div>
                    </div>
                    <div className="space-y-1">
                        <label className="text-xs font-medium text-text-secondary uppercase">Telefoni</label>
                        <div className="relative">
                            <Phone className="absolute left-3 top-2.5 h-4 w-4 text-text-muted" />
                            <input 
                                type="tel" 
                                value={formData.phone}
                                onChange={e => setFormData({...formData, phone: e.target.value})}
                                className="glass-input w-full pl-9 pr-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-primary-start outline-none transition-all"
                                placeholder="+383 4x xxx xxx"
                            />
                        </div>
                    </div>
                </div>
                
                <div className="space-y-1">
                    <label className="text-xs font-medium text-text-secondary uppercase">Mesazhi</label>
                    <textarea 
                        required rows={4}
                        value={formData.message}
                        onChange={e => setFormData({...formData, message: e.target.value})}
                        className="glass-input w-full px-3 py-2.5 rounded-xl text-sm focus:ring-2 focus:ring-primary-start outline-none resize-none transition-all"
                        placeholder="Si mund t'ju ndihmojmë?"
                    />
                </div>

                <button 
                    type="submit" 
                    disabled={isSending}
                    className="btn-primary w-full py-3 rounded-xl font-semibold flex items-center justify-center gap-2 text-sm sm:text-base disabled:opacity-50"
                >
                    {isSending ? 'Duke dërguar...' : <><Send size={18} /> Dërgo Mesazhin</>}
                </button>
              </form>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
};

export default ContactModal;