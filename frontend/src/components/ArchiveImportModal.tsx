// FILE: src/components/ArchiveImportModal.tsx
// PHOENIX PROTOCOL - ARCHIVE SELECTOR MODAL V2.2 (SCOPE FIX)
// 1. FIX: Now passes 'caseId' to API to enforce strict case-scoped filtering.
// 2. RESULT: Modal only shows files belonging to the current case.

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
      // PHOENIX FIX: Added 'caseId' as second argument (was undefined). 
      // This forces the backend to filter items by the current Case ID.
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
          // Note: If multi-select is desired later, change this logic.
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
        className="fixed inset-0 bg-black/90 backdrop-blur-sm flex items-center justify-center z-[9999] p-4"
        onClick={onClose}
      >
        <motion.div 
          initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
          className="bg-background-dark w-full max-w-2xl rounded-2xl border border-glass-edge shadow-2xl overflow-hidden flex flex-col h-[600px]"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 border-b border-white/10 flex justify-between items-center bg-background-light/30">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Folder className="text-primary-400" /> Importo nga Arkiva
            </h2>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors">
              <X size={20} />
            </button>
          </div>

          {/* Breadcrumbs & Nav */}
          <div className="px-4 py-3 bg-black/20 border-b border-white/5 flex items-center gap-2 text-sm text-gray-300">
            {breadcrumbs.length > 1 && (
              <button onClick={handleBack} className="p-1 hover:bg-white/10 rounded mr-2 text-primary-400">
                <ArrowLeft size={16} />
              </button>
            )}
            {breadcrumbs.map((crumb, idx) => (
              <React.Fragment key={idx}>
                {idx > 0 && <ChevronRight size={12} className="text-gray-600" />}
                <span className={idx === breadcrumbs.length - 1 ? "text-white font-medium" : "text-gray-500"}>
                  {crumb.title}
                </span>
              </React.Fragment>
            ))}
          </div>

          {/* List Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
            {loading ? (
              <div className="flex justify-center items-center h-full text-gray-500">
                <Loader2 className="animate-spin mr-2" /> Duke ngarkuar...
              </div>
            ) : items.length === 0 ? (
              <div className="text-center text-gray-500 mt-10">
                 <div className="bg-white/5 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                    <Folder className="text-gray-600" size={30}/>
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
                        ${item.item_type === 'FOLDER' ? 'cursor-pointer hover:bg-white/10 border-white/5 bg-white/5' : ''}
                        ${item.item_type === 'FILE' && isSelected ? 'cursor-pointer bg-primary-900/20 border-primary-500/50' : ''}
                        ${item.item_type === 'FILE' && !isSelected && !isDisabled ? 'cursor-pointer bg-white/5 border-white/5 hover:bg-white/10' : ''}
                        ${isDisabled ? 'opacity-50 cursor-not-allowed bg-black/20 border-transparent' : ''}
                    `}
                  >
                    <div className="flex items-center gap-3">
                      {item.item_type === 'FOLDER' ? (
                        <Folder className="text-yellow-500" size={20} />
                      ) : (
                        <FileText className="text-blue-400" size={20} />
                      )}
                      <span className={`text-sm ${isSelected ? 'text-white font-medium' : 'text-gray-300'}`}>{item.title}</span>
                    </div>
                    {item.item_type === 'FILE' && (
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${isSelected ? 'bg-primary-500 border-primary-500' : 'border-gray-600'}`}>
                        {isSelected && <Check size={12} className="text-white" />}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Actions */}
          <div className="p-4 border-t border-white/10 bg-background-light/10 flex justify-between items-center">
            <span className="text-sm text-gray-400">
                {selectedIds.size === 0 
                    ? "Zgjidhni një dokument" 
                    : "1 dokument i zgjedhur"}
            </span>
            <button 
              onClick={handleImport}
              disabled={selectedIds.size === 0 || importing}
              className="px-6 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl font-bold transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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