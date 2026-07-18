import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useLockBodyScroll } from '../hooks/useLockBodyScroll';

interface NavigationItem {
  label: string;
  href: string;
  icon: React.ReactNode;
}

interface MobileSidebarProps {
  isOpen: boolean;
  onClose: () => void;
  items: NavigationItem[];
  currentPath: string;
  onNavigate: (href: string) => void;
}

export const MobileSidebar: React.FC<MobileSidebarProps> = ({
  isOpen,
  onClose,
  items,
  currentPath,
  onNavigate,
}) => {
  // Prevent body scroll when mobile navigation is active
  useLockBodyScroll(isOpen);

  const sidebarVariants = {
    closed: {
      x: '-100%',
      transition: {
        type: 'spring',
        stiffness: 380,
        damping: 35,
      },
    },
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 380,
        damping: 32,
      },
    },
  };

  const backdropVariants = {
    closed: { opacity: 0 },
    open: { opacity: 1 },
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          {/* Backdrop Overlay */}
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            initial="closed"
            animate="open"
            exit="closed"
            variants={backdropVariants}
            transition={{ duration: 0.2 }}
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Slide-over Panel */}
          <motion.div
            className="fixed bottom-0 top-0 left-0 flex flex-col w-full max-w-xs bg-canvas border-r border-main shadow-2xl overflow-hidden"
            initial="closed"
            animate="open"
            exit="closed"
            variants={sidebarVariants}
            role="dialog"
            aria-modal="true"
          >
            {/* Header Area */}
            <div className="flex items-center justify-between h-16 px-6 border-b border-main bg-surface">
              <span className="font-bold text-text-primary tracking-tight">
                JURISTI
              </span>
              <button
                type="button"
                onClick={onClose}
                className="flex items-center justify-center w-11 h-11 rounded-lg text-text-muted hover:text-text-primary hover:bg-hover transition-colors focus:outline-none focus:ring-2 focus:ring-primary-start"
                style={{ minWidth: '44px', minHeight: '44px' }}
                aria-label="Close menu"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Navigation Options */}
            <nav className="flex-1 px-4 py-6 overflow-y-auto custom-finance-scroll space-y-2">
              {items.map((item) => {
                const isActive = currentPath === item.href;
                return (
                  <button
                    key={item.href}
                    onClick={() => {
                      onNavigate(item.href);
                      onClose();
                    }}
                    className={`flex items-center w-full px-4 rounded-xl font-medium transition-all focus:outline-none focus:ring-2 focus:ring-primary-start ${
                      isActive
                        ? 'bg-hover text-primary-start border-l-4 border-primary-start py-3'
                        : 'text-text-secondary hover:text-text-primary hover:bg-hover py-3.5'
                    }`}
                    style={{ minHeight: '48px' }} // Meets the 44px tap target standard
                  >
                    <span
                      className={`mr-4 transition-colors ${
                        isActive ? 'text-primary-start' : 'text-text-muted'
                      }`}
                    >
                      {item.icon}
                    </span>
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </nav>

            {/* Footer Area */}
            <div className="p-6 border-t border-main bg-surface">
              <div className="flex items-center space-x-3">
                <div className="w-2.5 h-2.5 rounded-full bg-status-success" />
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">
                  Secure Connection Verified
                </span>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};