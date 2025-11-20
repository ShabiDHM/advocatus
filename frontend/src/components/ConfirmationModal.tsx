// FILE: src/components/ConfirmationModal.tsx
// PHOENIX PROTOCOL - MOBILE OPTIMIZATION
// 1. BUTTONS: Stacked vertically (full-width) on mobile for better ergonomics.
// 2. ICON: Replaced HTML entity with Lucide 'X' icon.
// 3. LAYOUT: Responsive flex direction (column on mobile, row on desktop).

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
    <div className="fixed inset-0 bg-background-dark bg-opacity-80 flex items-center justify-center z-50 p-4">
      
      <motion.div 
        className="w-full max-w-sm bg-background-light/70 backdrop-blur-md border border-glass-edge rounded-2xl shadow-2xl glow-primary/20 p-6 space-y-4"
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <div className="flex justify-between items-center border-b border-glass-edge/50 pb-3">
          <h3 className="text-xl font-bold text-text-primary">{title}</h3>
          <motion.button 
            className="text-text-secondary hover:text-red-500 p-1 transition-colors rounded-full hover:bg-white/5" 
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
        
        {/* PHOENIX FIX: Stack buttons vertically on mobile, row on desktop */}
        <div className="flex flex-col-reverse sm:flex-row sm:justify-end gap-3 pt-2">
          <motion.button 
            className="w-full sm:w-auto px-4 py-3 sm:py-2 rounded-xl text-text-secondary hover:text-text-primary bg-background-dark/50 border border-glass-edge transition-colors font-medium" 
            onClick={onClose}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            Cancel
          </motion.button>
          
          <motion.button 
            className="w-full sm:w-auto text-white font-semibold py-3 sm:py-2 px-4 rounded-xl transition-all duration-300 shadow-lg 
                       bg-gradient-to-r from-red-600 to-red-800 hover:from-red-500 hover:to-red-700 glow-accent" 
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