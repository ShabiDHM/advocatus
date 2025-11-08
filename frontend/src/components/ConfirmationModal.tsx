// frontend/src/components/ConfirmationModal.tsx
// DEFINITIVE VERSION 2.0 - DESIGN TRANSPLANT: Applied Revolutionary Design Transformation to Modal

import { motion } from 'framer-motion'; // NEW: For Interactive elements

interface ConfirmationModalProps {
  title: string;
  message: string;
  confirmText: string;
  onConfirm: () => void;
  onClose: () => void;
}

export function ConfirmationModal({ title, message, confirmText, onConfirm, onClose }: ConfirmationModalProps) {
  return (
    // DESIGN: Modal Overlay (Dark, semi-transparent)
    <div className="fixed inset-0 bg-background-dark bg-opacity-80 flex items-center justify-center z-50 p-4">
      
      {/* DESIGN: Modal Body with Glass Morphism */}
      <motion.div 
        className="w-full max-w-sm bg-background-light/70 backdrop-blur-md border border-glass-edge rounded-2xl shadow-2xl glow-primary/20 p-6 space-y-4"
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
      >
        <div className="flex justify-between items-center border-b border-glass-edge/50 pb-3">
          {/* DESIGN: New text colors */}
          <h3 className="text-xl font-bold text-text-primary">{title}</h3>
          <motion.button 
            className="text-text-secondary hover:text-red-500 text-3xl transition-colors" 
            onClick={onClose}
            whileHover={{ scale: 1.2, rotate: 90 }}
          >
            &times;
          </motion.button>
        </div>
        
        {/* DESIGN: Message text color */}
        <div className="text-text-secondary">{message}</div>
        
        <div className="flex justify-end gap-3 pt-2">
          {/* DESIGN: Secondary (Cancel) Button */}
          <motion.button 
            className="px-4 py-2 rounded-xl text-text-secondary hover:text-text-primary bg-background-dark/50 border border-glass-edge transition-colors" 
            onClick={onClose}
            whileHover={{ scale: 1.05 }}
          >
            Cancel
          </motion.button>
          
          {/* DESIGN: Primary (Confirm/Danger) Button - Gradient & Glow (Red) */}
          <motion.button 
            className="text-white font-semibold py-2 px-4 rounded-xl transition-all duration-300 shadow-lg 
                       bg-gradient-to-r from-red-600 to-red-800 hover:from-red-500 hover:to-red-700 glow-accent" 
            onClick={onConfirm}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.98 }}
          >
            {confirmText}
          </motion.button>
        </div>
      </motion.div>
    </div>
  );
}