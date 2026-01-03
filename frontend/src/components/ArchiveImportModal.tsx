// FILE: src/components/ArchiveImportModal.tsx
// PHOENIX PROTOCOL - ARCHIVE MODAL V3.1 (ROBUST FILTERING)
// 1. FIX: Improved filtering to check file_type and MIME types, not just title extensions.
// 2. LOGIC: Ensures files named without extensions (e.g. "Contract") still appear if their type matches.

import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Folder, FileText, ChevronRight, ArrowLeft, Loader2, Check, File } from 'lucide-react';
import { apiService } from '../services/api';
import { ArchiveItemOut } from '../data/types';

interface ArchiveImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseId: string;
  onImportComplete?: (count: number) => void;
  onSelectFile?: (file: ArchiveItemOut) => void;
  mode?: 'import' | 'select';
  allowedExtensions?: string[]; // e.g. ['pdf', 'docx']
}

const ArchiveImportModal: React.FC<ArchiveImportModalProps> = ({ 
    isOpen, onClose, caseId, onImportComplete, onSelectFile, mode = 'import', allowedExtensions 
}) => {
  const [currentFolderId, setCurrentFolderId] = useState<string | undefined>(undefined);
  const [items, setItems] = useState<ArchiveItemOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  
  const [breadcrumbs, setBreadcrumbs] = useState<{id: string | undefined, title: string}[]>([{id: undefined, title: 'Arkiva'}]);

  useEffect(() => {
    if (isOpen) {
        fetchItems(currentFolderId);
        setSelectedIds(new Set());
    }
  }, [isOpen, currentFolderId]);

  const fetchItems = async (parentId?: string) => {
    setLoading(true);
    try {
      // 1. Fetch items filtered by Case ID
      const data = await apiService.getArchiveItems(undefined, caseId, parentId);
      
      // 2. Client-side filtering for 'select' mode
      let filteredData = data;
      if (mode === 'select' && allowedExtensions && allowedExtensions.length > 0) {
          filteredData = data.filter(item => {
              // Always show folders so we can navigate
              if (item.item_type === 'FOLDER') return true;
              
              // Check 1: Title Extension (e.g. "file.pdf")
              const titleExt = item.title.split('.').pop()?.toLowerCase() || '';
              
              // Check 2: Database File Type (e.g. "pdf", "docx")
              const typeExt = item.file_type?.toLowerCase() || '';
              
              // Check 3: Fuzzy MIME Type matching
              let mimeMatch = false;
              if (typeExt.includes('pdf')) mimeMatch = allowedExtensions.includes('pdf');
              if (typeExt.includes('word') || typeExt.includes('officedocument') || typeExt.includes('docx')) {
                  mimeMatch = allowedExtensions.includes('docx') || allowedExtensions.includes('doc');
              }
              if (typeExt.includes('sheet') || typeExt.includes('excel') || typeExt.includes('spreadsheet')) {
                  mimeMatch = allowedExtensions.includes('xlsx') || allowedExtensions.includes('xls') || allowedExtensions.includes('csv');
              }
              if (typeExt.includes('text') || typeExt.includes('csv')) {
                  mimeMatch = allowedExtensions.includes('txt') || allowedExtensions.includes('csv');
              }

              return allowedExtensions.includes(titleExt) || allowedExtensions.includes(typeExt) || mimeMatch;
          });
      }
      
      setItems(filteredData);
    } catch (error) {
      console.error("Failed to load archive items", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFolderClick = (folder: ArchiveItemOut) => {
    setBreadcrumbs(prev => [...prev, { id: folder.id, title: folder.title }]);
    setCurrentFolderId(folder.id);
    setSelectedIds(new Set());
  };

  const handleBack = () => {
    if (breadcrumbs.length <= 1) return;
    const newBreadcrumbs = [...breadcrumbs];
    newBreadcrumbs.pop(); 
    const parent = newBreadcrumbs[newBreadcrumbs.length - 1];
    setBreadcrumbs(newBreadcrumbs);
    setCurrentFolderId(parent.id);
    setSelectedIds(new Set());
  };

  const toggleSelection = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set<string>();
      if (prev.has(id)) return newSet; // Deselect not really supported in single select logic here effectively
      
      // In select mode for analysis, strictly single select
      if (mode === 'select') {
          newSet.add(id);
          return newSet;
      }
      
      // In import mode, maybe multi? Keeping single for consistency unless requested otherwise
      newSet.add(id);
      return newSet;
    });
  };

  const handleSubmit = async () => {
    if (selectedIds.size === 0) return;
    const selectedId = Array.from(selectedIds)[0];

    // MODE: SELECT (Analyst)
    if (mode === 'select' && onSelectFile) {
        const item = items.find(i => i.id === selectedId);
        if (item) {
            onSelectFile(item);
            onClose();
        }
        return;
    }

    // MODE: IMPORT (Copy to Case)
    setImporting(true);
    try {
      await apiService.importArchiveDocuments(caseId, Array.from(selectedIds));
      if (onImportComplete) onImportComplete(selectedIds.size);
      onClose();
    } catch (error) {
      alert("Import failed.");
    } finally {
      setImporting(false);
    }
  };

  // Helper for icons
  const getIcon = (item: ArchiveItemOut) => {
      if (item.item_type === 'FOLDER') return <Folder className="text-yellow-500" size={20} />;
      const ext = item.title.split('.').pop()?.toLowerCase();
      if (['pdf', 'docx', 'doc', 'txt'].includes(ext || '')) return <FileText className="text-blue-400" size={20} />;
      if (['xls', 'xlsx', 'csv'].includes(ext || '')) return <FileText className="text-green-400" size={20} />;
      return <File className="text-gray-400" size={20} />;
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
          className="bg-gray-900 w-full max-w-2xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col h-[600px]"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 border-b border-white/10 flex justify-between items-center bg-white/5">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Folder className="text-blue-400" /> 
              {mode === 'select' ? 'Zgjidhni nga Arkiva' : 'Importo nga Arkiva'}
            </h2>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors">
              <X size={20} />
            </button>
          </div>

          {/* Breadcrumbs */}
          <div className="px-4 py-3 bg-black/20 border-b border-white/5 flex items-center gap-2 text-sm text-gray-300">
            {breadcrumbs.length > 1 && (
              <button onClick={handleBack} className="p-1 hover:bg-white/10 rounded mr-2 text-blue-400">
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
                 <p>Dosja është e zbrazët.</p>
                 <p className="text-xs mt-2 opacity-50">(Kontrolloni nëse keni ngarkuar dokumente në këtë Rast)</p>
              </div>
            ) : (
              items.map(item => {
                const isSelected = selectedIds.has(item.id);
                // In select mode, disable files that are already selected? No, single select replaces.
                // Just highlight logic.
                
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
                        ${item.item_type === 'FILE' && isSelected ? 'cursor-pointer bg-blue-900/20 border-blue-500/50' : ''}
                        ${item.item_type === 'FILE' && !isSelected ? 'cursor-pointer bg-white/5 border-white/5 hover:bg-white/10' : ''}
                    `}
                  >
                    <div className="flex items-center gap-3">
                      {getIcon(item)}
                      <div className="flex flex-col">
                          <span className={`text-sm ${isSelected ? 'text-white font-medium' : 'text-gray-300'}`}>{item.title}</span>
                          {/* Optional debug info if needed: <span className="text-[10px] text-gray-600">{item.file_type}</span> */}
                      </div>
                    </div>
                    {item.item_type === 'FILE' && (
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors ${isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-600'}`}>
                        {isSelected && <Check size={12} className="text-white" />}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/10 bg-white/5 flex justify-between items-center">
            <span className="text-sm text-gray-400">
                {selectedIds.size === 0 ? "Zgjidhni një dokument" : "1 dokument i zgjedhur"}
            </span>
            <button 
              onClick={handleSubmit}
              disabled={selectedIds.size === 0 || importing}
              className="px-6 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-xl font-bold transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {importing ? <Loader2 className="animate-spin" size={16} /> : null}
              {mode === 'select' ? 'Përdor Dokumentin' : (importing ? "Duke importuar..." : "Shto në Rast")}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>,
    document.body
  );
};

export default ArchiveImportModal;