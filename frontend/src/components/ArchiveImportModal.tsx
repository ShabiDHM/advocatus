// FILE: src/components/ArchiveImportModal.tsx
// PHOENIX PROTOCOL - RESPONSIVE FIX V3.2
// 1. FIX: Replaced fixed height with 'max-h-[85vh]' to prevent overflow on mobile.
// 2. UI: Adjusted padding for better visibility on small screens.

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
  allowedExtensions?: string[];
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
      const data = await apiService.getArchiveItems(undefined, caseId, parentId);
      
      let filteredData = data;
      if (mode === 'select' && allowedExtensions && allowedExtensions.length > 0) {
          filteredData = data.filter(item => {
              if (item.item_type === 'FOLDER') return true;
              
              const titleExt = item.title.split('.').pop()?.toLowerCase() || '';
              const typeExt = item.file_type?.toLowerCase() || '';
              
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
      if (prev.has(id)) return newSet;
      newSet.add(id);
      return newSet;
    });
  };

  const handleSubmit = async () => {
    if (selectedIds.size === 0) return;
    const selectedId = Array.from(selectedIds)[0];

    if (mode === 'select' && onSelectFile) {
        const item = items.find(i => i.id === selectedId);
        if (item) {
            onSelectFile(item);
            onClose();
        }
        return;
    }

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
          // PHOENIX FIX: Removed h-[600px], added max-h-[85vh]
          className="bg-gray-900 w-full max-w-2xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]"
          onClick={e => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-4 border-b border-white/10 flex justify-between items-center bg-white/5 flex-shrink-0">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Folder className="text-blue-400" /> 
              {mode === 'select' ? 'Zgjidhni nga Arkiva' : 'Importo nga Arkiva'}
            </h2>
            <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors">
              <X size={20} />
            </button>
          </div>

          {/* Breadcrumbs */}
          <div className="px-4 py-2 bg-black/20 border-b border-white/5 flex items-center gap-2 text-sm text-gray-300 flex-shrink-0">
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
          <div className="flex-1 overflow-y-auto p-2 sm:p-4 space-y-2 custom-scrollbar">
            {loading ? (
              <div className="flex justify-center items-center h-full text-gray-500">
                <Loader2 className="animate-spin mr-2" /> Duke ngarkuar...
              </div>
            ) : items.length === 0 ? (
              <div className="text-center text-gray-500 py-10">
                 <div className="bg-white/5 p-4 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                    <Folder className="text-gray-600" size={30}/>
                 </div>
                 <p>Dosja është e zbrazët.</p>
                 <p className="text-xs mt-2 opacity-50">(Kontrolloni nëse keni ngarkuar dokumente në këtë Rast)</p>
              </div>
            ) : (
              items.map(item => {
                const isSelected = selectedIds.has(item.id);
                
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
                    <div className="flex items-center gap-3 min-w-0">
                      {getIcon(item)}
                      <div className="flex flex-col min-w-0">
                          <span className={`text-sm truncate ${isSelected ? 'text-white font-medium' : 'text-gray-300'}`}>{item.title}</span>
                      </div>
                    </div>
                    {item.item_type === 'FILE' && (
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center transition-colors flex-shrink-0 ${isSelected ? 'bg-blue-500 border-blue-500' : 'border-gray-600'}`}>
                        {isSelected && <Check size={12} className="text-white" />}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-white/10 bg-white/5 flex justify-between items-center flex-shrink-0">
            <span className="text-sm text-gray-400 truncate">
                {selectedIds.size === 0 ? "Zgjidhni një dokument" : "1 dokument i zgjedhur"}
            </span>
            <button 
              onClick={handleSubmit}
              disabled={selectedIds.size === 0 || importing}
              className="px-4 sm:px-6 py-2 bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white rounded-xl font-bold transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
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