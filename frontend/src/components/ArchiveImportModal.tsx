// FILE: src/components/ArchiveImportModal.tsx
// PHOENIX PROTOCOL - ARCHIVE SELECTOR MODAL V6.0 (EXECUTIVE DESIGN SYSTEM)
// 1. Converted to semantic classes: bg-canvas, glass-panel, border-main, text-text-primary, text-text-secondary, text-text-muted, btn-primary.
// 2. Preserved all functionality and case-scoped filtering.
// 3. Consistent with other modals and pages.

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Folder, FileText, ChevronRight, ArrowLeft, Loader2, Check } from 'lucide-react';
import { apiService } from '../services/api';
import { ArchiveItemOut } from '../data/types';

interface ArchiveImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  onImportComplete: (count: number) => void;
}

const ArchiveImportModal: React.FC<ArchiveImportModalProps> = ({ isOpen, onClose, caseId, onImportComplete }) => {
  const [currentFolderId, setCurrentFolderId] = useState<string | undefined>(undefined);
  const [items, setItems] = useState<ArchiveItemOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  
  const [breadcrumbs, setBreadcrumbs] = useState<{id: string | undefined, title: string}[]>([{id: undefined, title: 'Arkiva'}]);

  useEffect(() => {
    if (isOpen) fetchItems(currentFolderId);
  }, [isOpen, currentFolderId]);

  const fetchItems = async (parentId?: string) => {
    setLoading(true);
    try {
      const data = await apiService.getArchiveItems(undefined, caseId, parentId);
      setItems(data);
    } catch (error) {
      console.error("Failed to load archive items", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFolderClick = (folder: ArchiveItemOut) => {
    setBreadcrumbs(prev => [...prev, { id: folder.id, title: folder.title }]);
    setCurrentFolderId(folder.id);
    setSelectedIds(new Set()); // Clear selection when changing folders
  };

  const handleBack = () => {
    if (breadcrumbs.length <= 1) return;
    const newBreadcrumbs = [...breadcrumbs];
    newBreadcrumbs.pop(); 
    const parent = newBreadcrumbs[newBreadcrumbs.length - 1];
    setBreadcrumbs(newBreadcrumbs);
    setCurrentFolderId(parent.id);
    setSelectedIds(new Set()); // Clear selection on back
  };

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set<string>();
      if (prev.has(id)) {
          // If clicking the already selected one, deselect it (empty set)
          return newSet; 
      } else {
          // Otherwise, select ONLY this one (Single Selection Mode for Import)
          newSet.add(id);
          return newSet;
      }
    });
  };

  const handleImport = async () => {
    if (selectedIds.size === 0) return;
    setImporting(true);
    try {
      await apiService.importArchiveDocuments(caseId, Array.from(selectedIds));
      onImportComplete(selectedIds.size);
      onClose();
    } catch (error) {
      alert("Import failed.");
    } finally {
      setImporting(false);
    }
  };

  if (!isOpen) return null;

  return ReactDOM.createPortal(
    <AnimatePresence>
      <motion.div 
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 bg-canvas/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
          className="glass-panel border border-main w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[600px]"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 border-b border-main flex justify-between items-center bg-surface/20">
            <h2 className="text-lg font-bold text-text-primary flex items-center gap-2">
              <Folder className="text-primary-start" /> Importo nga Arkiva
            </h2>
            <button onClick={onClose} className="p-2 hover:bg-surface/50 rounded-full text-text-muted hover:text-text-primary transition-colors">
              <X size={20} />
            </button>
          </div>

          {/* Breadcrumbs & Nav */}
          <div className="px-4 py-3 bg-canvas/40 border-b border-main flex items-center gap-2 text-sm text-text-secondary">
            {breadcrumbs.length > 1 && (
              <button onClick={handleBack} className="p-1 hover:bg-surface/50 rounded mr-2 text-primary-start">
                <ArrowLeft size={16} />
              </button>
            )}
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight size={12} className="text-text-muted" />}
                <span className={idx === breadcrumbs.length - 1 ? "text-text-primary font-medium" : "text-text-muted"}>
                  {crumb.title}
                </span>
              </React.Fragment>
            ))}
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
            {loading ? (
              <div className="flex justify-center items-center h-full text-text-muted">
                <Loader2 className="animate-spin mr-2" /> Duke ngarkuar...
              </div>
            ) : items.length === 0 ? (
              <div className="text-center text-text-muted mt-10">
                 <div className="bg-surface/30 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                    <Folder className="text-text-muted" size={30}/>
                 </div>
                 Dosja është e zbrazët.
              </div>
            ) : (
              items.map(item => {
                const isSelected = selectedIds.has(item.id);
                // Disable other files if one is already selected (Visual hint)
                const isDisabled = selectedIds.size > 0 && !isSelected && item.item_type === 'FILE';
                
                return (
                  <div 
                    key={item.id}
                    onClick={() => {
                        if (item.item_type === 'FOLDER') handleFolderClick(item);
                        else toggleSelection(item.id);
                    }}
                    className={`
                        flex items-center justify-between p-3 rounded-xl border transition-all 
                        ${item.item_type === 'FOLDER' ? 'cursor-pointer hover:bg-surface/30 border-main bg-surface/10' : ''}
                        ${item.item_type === 'FILE' && isSelected ? 'cursor-pointer bg-primary-start/10 border-primary-start/50' : ''}
                        ${item.item_type === 'FILE' && !isSelected && !isDisabled ? 'cursor-pointer bg-surface/10 border-main hover:bg-surface/30' : ''}
                        ${isDisabled ? 'opacity-50 cursor-not-allowed bg-surface/5 border-transparent' : ''}
                    `}
                  >
                    <div className="flex items-center gap-3">
                      {item.item_type === 'FOLDER' ? (
                        <Folder className="text-secondary-start" size={20} />
                      ) : (
                        <FileText className="text-primary-start" size={20} />
                      )}
                      <span className={`text-sm ${isSelected ? 'text-text-primary font-medium' : 'text-text-secondary'}`}>{item.title}</span>
                    </div>
                    {item.item_type === 'FILE' && (
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${isSelected ? 'bg-primary-start border-primary-start' : 'border-text-muted'}`}>
                        {isSelected && <Check size={12} className="text-text-primary" />}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-main bg-surface/10 flex justify-between items-center">
            <span className="text-sm text-text-muted">
                {selectedIds.size === 0 
                    ? "Zgjidhni një dokument" 
                    : "1 dokument i zgjedhur"}
            </span>
            <button 
              onClick={handleImport}
              disabled={selectedIds.size === 0 || importing}
              className="btn-primary px-6 py-2 rounded-xl font-bold transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {importing ? <Loader2 className="animate-spin" size={16} /> : null}
              {importing ? "Duke importuar..." : "Shto në Rast"}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
};

export default ArchiveImportModal;