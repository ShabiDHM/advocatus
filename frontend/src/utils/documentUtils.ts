// FILE: /home/user/advocatus-frontend/src/utils/documentUtils.ts
// PHOENIX PROTOCOL MODIFICATION 18.0 (ARCHITECTURAL DATA ALIGNMENT):
// 1. CRITICAL FIX: The function's logic has been completely rewritten to align with the
//    refactored `Document` data contract in `types.ts`.
// 2. It no longer corrupts the data by creating an obsolete `uploadedAt` field. Instead,
//    it now correctly preserves the `created_at` property.
// 3. This resolves the root cause of the unhandled TypeError and the resulting blank screen.
// 4. AGGRESSIVE CLEANUP: The function now explicitly removes all known obsolete fields,
//    ensuring the returned object perfectly matches the `Document` interface.
//
// DEFINITIVE VERSION 1.0
// ...

import { Document } from '../data/types';

export const sanitizeDocument = (doc: any): Document => {
    // 1. Ensure 'id' is the primary identifier, falling back to '_id' from MongoDB.
    const id = doc.id || doc._id;

    // 2. Ensure 'created_at' is the primary date field, falling back from the legacy 'uploadedAt' if present.
    const created_at = doc.created_at || doc.uploadedAt;

    // 3. Create a new object with the correct, standardized structure.
    const newDoc = { ...doc, id, created_at };
    
    // 4. Aggressively remove all redundant, backend-specific, or obsolete fields
    //    to guarantee the final object perfectly matches the frontend's Document type.
    delete newDoc._id;
    delete newDoc.uploadedAt;
    delete newDoc.caseId;
    delete newDoc.name;
    delete newDoc.type;
    delete newDoc.file_type;
    delete newDoc.upload_date;
    
    return newDoc as Document;
};