// FILE: src/utils/documentUtils.ts
// PHOENIX PROTOCOL - DOCUMENT UTILS V19.0 (PRESERVE PAGE_COUNT & ACCURATE METADATA)

import { Document } from '../data/types';

export const sanitizeDocument = (doc: any): Document => {
    if (!doc) return doc;

    // 1. Sigurojmë 'id' primare nga id ose _id e MongoDB
    const id = doc.id || doc._id;

    // 2. Sigurojmë datën e krijimit
    const created_at = doc.created_at || doc.uploadedAt || new Date().toISOString();

    // 3. Sigurojmë numrin real të faqeve nga çdo variacion i mundshëm i emrit
    const rawPageCount = doc.page_count || doc.pages || doc.total_pages || doc.num_pages || 1;
    const page_count = typeof rawPageCount === 'number' ? rawPageCount : (parseInt(String(rawPageCount), 10) || 1);

    // 4. Krijojmë objektin e standardizuar me të gjitha fushat
    const newDoc = { 
        ...doc, 
        id, 
        created_at, 
        page_count, 
        pages: page_count 
    };
    
    // 5. Pastrojmë fushat e vjetra/redundante
    delete newDoc._id;
    delete newDoc.uploadedAt;
    delete newDoc.caseId;
    delete newDoc.upload_date;
    
    return newDoc as Document;
};