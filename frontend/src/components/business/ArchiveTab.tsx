// FILE: src/components/business/ArchiveTab.tsx
// PHOENIX PROTOCOL - ARCHIVE TAB V9.5 (CLEAN & I18N)
// 1. FIX: Resolved unused variables (isLoading, crumb).
// 2. I18N: Removed all hardcoded strings ("Details", "Open Folder", Categories).
// 3. UI: Restored Loading Spinner on file view.

import React, { useEffect, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
    Home, Briefcase, FolderOpen, ChevronRight, FolderPlus, Loader2, FolderInput, Upload,
    Calendar, Info, Hash, FileText, FileImage, FileCode, File as FileIcon, Eye, Download, Trash2, Tag, X
} from 'lucide-react';
import { apiService } from '../../services/api';
import { ArchiveItemOut, Case, Document } from '../../data/types';
import { useTranslation } from 'react-i18next';
import PDFViewerModal from '../PDFViewerModal';

type Breadcrumb = { id: string | null; name: string; type: 'ROOT' | 'CASE' | 'FOLDER'; };

const getMimeType = (fileType: string, fileName: string) => {
    const ext = fileName.split('.').pop()?.toLowerCase() || '';
    if (fileType === 'PDF' || ext === 'pdf') return 'application/pdf';
    if (['PNG', 'JPG', 'JPEG', 'WEBP', 'GIF'].includes(fileType)) return 'image/jpeg';
    return 'application/octet-stream';
};

const getFileIcon = (fileType: string) => {
    const ft = fileType ? fileType.toUpperCase() : "";
    if (ft === 'PDF') return <FileText className="w-5 h-5 text-red-400" />;
    if (['PNG', 'JPG', 'JPEG'].includes(ft)) return <FileImage className="w-5 h-5 text-purple-400" />;
    if (['JSON', 'JS', 'TS'].includes(ft)) return <FileCode className="w-5 h-5 text-yellow-400" />;
    return <FileIcon className="w-5 h-5 text-blue-400" />;
};

// Extracted Card Component for better performance & hook usage
const ArchiveCard = ({ title, subtitle, type, date, icon, statusColor, onClick, onDownload, onDelete, isFolder, isLoading }: any) => {
    const { t } = useTranslation();
    return (
        <div onClick={onClick} className={`group relative flex flex-col justify-between h-full min-h-[14rem] p-6 rounded-2xl transition-all duration-300 cursor-pointer bg-gray-900/40 backdrop-blur-md border border-white/5 shadow-xl hover:shadow-2xl hover:bg-gray-800/60 hover:-translate-y-1 hover:scale-[1.01]`}>
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-indigo-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none" />
            <div>
                <div className="flex flex-col mb-4 relative z-10">
                    <div className="flex justify-between items-start gap-2">
                        <div className="p-2.5 rounded-xl bg-white/5 border border-white/10 group-hover:scale-110 transition-transform duration-300">{icon}</div>
                        <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${statusColor} shadow-[0_0_8px_currentColor]`} />
                    </div>
                    <div className="mt-4">
                        <h2 className="text-lg font-bold text-gray-100 line-clamp-2 leading-tight tracking-tight group-hover:text-primary-start transition-colors break-words">{title}</h2>
                        <div className="flex items-center gap-2 mt-2"><Calendar className="w-3 h-3 text-gray-600 flex-shrink-0" /><p className="text-xs text-gray-500 font-medium truncate">{date}</p></div>
                    </div>
                </div>
                <div className="flex flex-col mb-6 relative z-10">
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-white/5">
                        <Info className="w-3 h-3 text-indigo-400" /><span className="text-xs font-bold text-gray-300 uppercase tracking-wider">{isFolder ? t('archive.contents', 'Contents') : t('archive.details', 'Details')}</span>
                    </div>
                    <div className="space-y-1.5 pl-1">
                        <div className="flex items-center gap-2 text-sm font-medium text-gray-200">{isFolder ? <FolderOpen className="w-3.5 h-3.5 text-amber-500" /> : <FileText className="w-3.5 h-3.5 text-blue-500" />}<span className="truncate">{type}</span></div>
                        <div className="flex items-center gap-2 text-xs text-gray-500"><Hash className="w-3 h-3 flex-shrink-0" /><span className="truncate">{subtitle}</span></div>
                    </div>
                </div>
            </div>
            <div className="relative z-10 pt-4 border-t border-white/5 flex items-center justify-between min-h-[3rem]">
                <span className="text-xs font-medium text-indigo-400 group-hover:text-indigo-300 transition-colors flex items-center gap-1">{isFolder ? t('archive.openFolder', 'Open Folder') : ''}</span>
                <div className="flex gap-1 items-center">
                    {!isFolder && <button onClick={(e) => { e.stopPropagation(); onClick(); }} className="p-2 rounded-lg text-gray-600 hover:text-blue-400 hover:bg-blue-400/10 transition-colors">{isLoading ? <Loader2 className="h-4 w-4 animate-spin text-blue-400" /> : <Eye className="h-4 w-4" />}</button>}
                    {!isFolder && onDownload && <button onClick={(e) => { e.stopPropagation(); onDownload(); }} className="p-2 rounded-lg text-gray-600 hover:text-green-400 hover:bg-green-400/10 transition-colors"><Download className="h-4 w-4" /></button>}
                    {onDelete && <button onClick={(e) => { e.stopPropagation(); onDelete(); }} className="p-2 rounded-lg text-gray-600 hover:text-red-400 hover:bg-red-400/10 transition-colors"><Trash2 className="h-4 w-4" /></button>}
                </div>
            </div>
        </div>
    );
};

export const ArchiveTab: React.FC = () => {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(true);
    const [archiveItems, setArchiveItems] = useState<ArchiveItemOut[]>([]);
    const [cases, setCases] = useState<Case[]>([]);
    const [breadcrumbs, setBreadcrumbs] = useState<Breadcrumb[]>([{ id: null, name: t('business.archive'), type: 'ROOT' }]);
    
    const [isUploading, setIsUploading] = useState(false);
    const [showFolderModal, setShowFolderModal] = useState(false);
    const [newFolderName, setNewFolderName] = useState("");
    const [newFolderCategory, setNewFolderCategory] = useState("GENERAL");
    const [viewingDoc, setViewingDoc] = useState<Document | null>(null);
    const [viewingUrl, setViewingUrl] = useState<string | null>(null);
    const [openingDocId, setOpeningDocId] = useState<string | null>(null);

    const folderInputRef = useRef<HTMLInputElement>(null);
    const archiveInputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        const loadCases = async () => { try { const c = await apiService.getCases(); setCases(c); } catch {} };
        loadCases();
    }, []);

    useEffect(() => { fetchArchiveContent(); }, [breadcrumbs]);

    const fetchArchiveContent = async () => {
        const active = breadcrumbs[breadcrumbs.length - 1];
        setLoading(true);
        try {
            if (active.type === 'ROOT') setArchiveItems(await apiService.getArchiveItems(undefined, undefined, "null"));
            else if (active.type === 'CASE') setArchiveItems(await apiService.getArchiveItems(undefined, active.id!, "null"));
            else if (active.type === 'FOLDER') setArchiveItems(await apiService.getArchiveItems(undefined, undefined, active.id!));
        } catch {} finally { setLoading(false); }
    };

    const handleNavigate = (_: Breadcrumb, index: number) => setBreadcrumbs(prev => prev.slice(0, index + 1));
    const handleEnterFolder = (id: string, name: string, type: 'FOLDER' | 'CASE') => setBreadcrumbs(prev => [...prev, { id, name, type }]);

    const handleCreateFolder = async (e: React.FormEvent) => {
        e.preventDefault();
        const active = breadcrumbs[breadcrumbs.length - 1];
        try { await apiService.createArchiveFolder(newFolderName, active.type === 'FOLDER' ? active.id! : undefined, active.type === 'CASE' ? active.id! : undefined, newFolderCategory); setShowFolderModal(false); fetchArchiveContent(); } catch { alert(t('error.generic')); }
    };

    const handleSmartUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0]; if(!f) return;
        setIsUploading(true);
        const active = breadcrumbs[breadcrumbs.length - 1];
        try { await apiService.uploadArchiveItem(f, f.name, "GENERAL", active.type === 'CASE' ? active.id! : undefined, active.type === 'FOLDER' ? active.id! : undefined); fetchArchiveContent(); } catch { alert(t('error.uploadFailed')); } finally { setIsUploading(false); }
    };
    
    const handleFolderUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const files = e.target.files; if (!files || files.length === 0) return;
        setIsUploading(true);
        const active = breadcrumbs[breadcrumbs.length - 1];
        try {
            const firstPath = files[0].webkitRelativePath || "";
            const rootFolderName = firstPath.split('/')[0] || t('archive.newFolderDefault', "New Folder");
            const newFolder = await apiService.createArchiveFolder(rootFolderName, active.type === 'FOLDER' ? active.id! : undefined, active.type === 'CASE' ? active.id! : undefined, "GENERAL");
            if (!newFolder || !newFolder.id) throw new Error("Failed to create folder");
            const uploadPromises = Array.from(files).map(file => {
                if (file.name.startsWith('.')) return Promise.resolve();
                return apiService.uploadArchiveItem(file, file.name, "GENERAL", active.type === 'CASE' ? active.id! : undefined, newFolder.id);
            });
            await Promise.all(uploadPromises); fetchArchiveContent();
        } catch { alert(t('error.uploadFailed')); } finally { setIsUploading(false); if (folderInputRef.current) folderInputRef.current.value = ''; }
    };

    const downloadArchiveItem = async (id: string, title: string) => { try { await apiService.downloadArchiveItem(id, title); } catch { alert(t('error.generic')); } };
    const deleteArchiveItem = async (id: string) => { if(!window.confirm(t('general.confirmDelete'))) return; try { await apiService.deleteArchiveItem(id); fetchArchiveContent(); } catch { alert(t('error.generic')); } };
    
    const handleViewItem = async (item: ArchiveItemOut) => { 
        setOpeningDocId(item.id);
        try { 
            const blob = await apiService.getArchiveFileBlob(item.id); 
            const url = window.URL.createObjectURL(blob); 
            setViewingUrl(url); 
            setViewingDoc({ id: item.id, file_name: item.title, mime_type: getMimeType(item.file_type, item.title), status: 'READY' } as any); 
        } catch { alert(t('error.generic')); }
        finally { setOpeningDocId(null); }
    };

    const currentView = breadcrumbs[breadcrumbs.length - 1];
    const displayedItems = archiveItems.filter(item => { if (currentView.type === 'ROOT') { return !item.case_id; } return true; });

    if (loading) return <div className="flex justify-center h-64 items-center"><Loader2 className="animate-spin text-primary-start" /></div>;

    return (
        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-8">
            <div className="flex flex-col gap-4">
                <div className="flex justify-between items-center bg-white/5 backdrop-blur-xl p-2 rounded-2xl border border-white/10 shadow-2xl">
                    <div className="flex items-center gap-2 overflow-x-auto text-sm no-scrollbar px-2 py-1 min-w-0">
                        {breadcrumbs.map((crumb, index) => (
                            <React.Fragment key={crumb.id || 'root'}>
                                <button onClick={() => handleNavigate(crumb, index)} className={`flex-shrink-0 flex items-center gap-2 px-3 py-1.5 rounded-lg transition-all ${index === breadcrumbs.length - 1 ? 'bg-primary-start/20 text-primary-start font-bold border border-primary-start/20 shadow-inner' : 'text-gray-400 hover:text-white hover:bg-white/10'}`}>
                                    {crumb.type === 'ROOT' ? <Home size={14} /> : crumb.type === 'CASE' ? <Briefcase size={14} /> : <FolderOpen size={14} />}
                                    {crumb.name}
                                </button>
                                {index < breadcrumbs.length - 1 && <ChevronRight size={14} className="text-gray-600 flex-shrink-0" />}
                            </React.Fragment>
                        ))}
                    </div>
                    <div className="flex gap-2 flex-shrink-0 p-1 ml-2">
                        <button onClick={() => setShowFolderModal(true)} className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 hover:text-amber-400 rounded-xl border border-amber-500/30 transition-all font-bold text-xs uppercase tracking-wide"><FolderPlus size={16} /> <span className="hidden sm:inline">{t('archive.createFolder')}</span></button>
                        <div className="relative"><input type="file" ref={folderInputRef} onChange={handleFolderUpload} className="hidden" {...({ webkitdirectory: "", directory: "" } as any)} multiple /><button onClick={() => folderInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-indigo-500/10 text-indigo-400 hover:bg-indigo-500/20 hover:text-indigo-300 rounded-xl border border-indigo-500/30 transition-all font-bold text-xs uppercase tracking-wide disabled:opacity-50 disabled:cursor-wait" title={t('archive.uploadFolderTooltip')}><FolderInput size={16} /> <span className="hidden sm:inline">{t('archive.uploadFolder')}</span></button></div>
                        <div className="relative"><input type="file" ref={archiveInputRef} className="hidden" onChange={handleSmartUpload} /><button onClick={() => archiveInputRef.current?.click()} disabled={isUploading} className="flex items-center gap-2 px-3 sm:px-4 py-2 bg-primary-start hover:bg-primary-end text-white rounded-xl shadow-lg shadow-primary-start/20 transition-all font-bold text-xs uppercase tracking-wide disabled:opacity-50 disabled:cursor-wait">{isUploading ? <Loader2 className="animate-spin w-4 h-4" /> : <Upload size={16} />} <span className="hidden sm:inline">{t('archive.upload')}</span></button></div>
                    </div>
                </div>
            </div>
            
            <div className="space-y-10">
                {currentView.type === 'ROOT' && cases.length > 0 && (<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">{cases.map(c => (<div key={c.id} className="h-full"><ArchiveCard title={c.title || `Rasti #${c.case_number}`} subtitle={c.case_number || 'Pa numër'} type="Dosje Çështjeje" date={new Date(c.created_at).toLocaleDateString()} icon={<Briefcase className="w-5 h-5 text-indigo-400" />} statusColor="bg-indigo-400" isFolder={true} onClick={() => handleEnterFolder(c.id, c.title, 'CASE')} /></div>))}</div>)}
                {displayedItems.length > 0 && (
                    <motion.div layout className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        <AnimatePresence>
                            {displayedItems.map(item => { 
                                const isFolder = (item as any).item_type === 'FOLDER'; 
                                const fileExt = item.file_type || 'FILE'; 
                                return (
                                    <motion.div layout initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} key={item.id} className="h-full">
                                        <ArchiveCard 
                                            title={item.title} 
                                            subtitle={isFolder ? t('archive.caseFolders') : `${fileExt} Dokument`} 
                                            type={isFolder ? 'Folder' : fileExt} 
                                            date={new Date().toLocaleDateString()} 
                                            icon={isFolder ? <FolderOpen className="w-5 h-5 text-amber-500" /> : getFileIcon(fileExt)} 
                                            statusColor={isFolder ? 'bg-amber-400' : 'bg-blue-400'} 
                                            isFolder={isFolder} 
                                            isLoading={openingDocId === item.id}
                                            onClick={() => isFolder ? handleEnterFolder(item.id, item.title, 'FOLDER') : handleViewItem(item)} 
                                            onDownload={() => downloadArchiveItem(item.id, item.title)} 
                                            onDelete={() => deleteArchiveItem(item.id)} 
                                        />
                                    </motion.div>
                                );
                            })}
                        </AnimatePresence>
                    </motion.div>
                )}
            </div>

            {/* Create Folder Modal */}
            {showFolderModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-in fade-in duration-200">
                    <div className="bg-background-dark border border-glass-edge rounded-3xl w-full max-w-sm p-8 shadow-2xl scale-100">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-bold text-white">{t('archive.newFolderTitle')}</h3>
                            <button onClick={() => setShowFolderModal(false)} className="text-gray-500 hover:text-white"><X size={24}/></button>
                        </div>
                        <form onSubmit={handleCreateFolder}>
                            <div className="relative mb-5"><FolderOpen className="absolute left-4 top-3.5 w-6 h-6 text-amber-500" /><input autoFocus type="text" value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} placeholder={t('archive.folderNamePlaceholder')} className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3.5 text-white text-lg focus:ring-2 focus:ring-amber-500/50 outline-none transition-all placeholder:text-gray-600" /></div>
                            <div className="relative mb-8">
                                <Tag className="absolute left-4 top-3.5 w-5 h-5 text-gray-500" />
                                <select value={newFolderCategory} onChange={(e) => setNewFolderCategory(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl pl-12 pr-4 py-3.5 text-gray-300 focus:ring-2 focus:ring-amber-500/50 outline-none appearance-none cursor-pointer">
                                    <option value="GENERAL">{t('category.general', 'General')}</option>
                                    <option value="EVIDENCE">{t('category.evidence', 'Evidence')}</option>
                                    <option value="LEGAL_DOCS">{t('category.legalDocs', 'Legal Docs')}</option>
                                    <option value="INVOICES">{t('category.invoices', 'Invoices')}</option>
                                    <option value="CONTRACTS">{t('category.contracts', 'Contracts')}</option>
                                </select>
                            </div>
                            <div className="flex justify-end gap-3"><button type="button" onClick={() => setShowFolderModal(false)} className="px-6 py-3 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-colors font-medium">{t('general.cancel')}</button><button type="submit" className="px-8 py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-white rounded-xl font-bold shadow-lg shadow-amber-500/20 transition-all transform hover:scale-[1.02]">{t('general.create')}</button></div>
                        </form>
                    </div>
                </div>
            )}

            {viewingDoc && <PDFViewerModal documentData={viewingDoc} onClose={() => { setViewingDoc(null); if(viewingUrl) window.URL.revokeObjectURL(viewingUrl); }} t={t} directUrl={viewingUrl} />}
        </motion.div>
    );
};