// FILE: src/components/ConfirmationModal.tsx
// PHOENIX PROTOCOL - CONFIRMATION MODAL V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: glass-panel, border-main, text-text-primary, text-text-secondary.
// 2. Buttons use btn-secondary and a danger variant (bg-danger-start).
// 3. Maintained mobile‑optimized stacking (column on mobile, row on desktop).
// 4. Preserved animations and close button.

import { motion } from 'framer-motion'; 
import { X } from 'lucide-react';

interface ConfirmationModalProps {
  title: string;
  message: string;
  confirmText: string;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmationModal({ title, message, confirmText, onConfirm, onClose }: ConfirmationModalProps) {
  return (
    <div className="fixed inset-0 bg-canvas/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      
      <motion.div 
        className="w-full max-w-sm glass-panel border border-main rounded-2xl shadow-2xl p-6 space-y-4"
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <div className="flex justify-between items-center border-b border-main pb-3">
          <h3 className="text-xl font-bold text-text-primary">{title}</h3>
          <motion.button 
            className="text-text-secondary hover:text-danger-start p-1 transition-colors rounded-full hover:bg-surface/30" 
            onClick={onClose}
            whileHover={{ scale: 1.1, rotate: 90 }}
            whileTap={{ scale: 0.9 }}
          >
            <X size={24} />
          </motion.button>
        </div>
        
        <div className="text-text-secondary text-sm sm:text-base leading-relaxed">
            {message}
        </div>
        
        {/* Buttons: stacked vertically on mobile, row on desktop */}
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-2">
          <motion.button 
            className="btn-secondary w-full sm:w-auto px-4 py-3 sm:py-2 rounded-xl font-medium" 
            onClick={onClose}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Cancel
          </motion.button>
          
          <motion.button 
            className="w-full sm:w-auto bg-danger-start hover:bg-danger-start/80 text-text-primary font-semibold py-3 sm:py-2 px-4 rounded-xl transition-all duration-300 shadow-lg" 
            onClick={onConfirm}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            {confirmText}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}