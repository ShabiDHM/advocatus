// FILE: frontend/src/services/api.ts
// PHOENIX PROTOCOL - MASTER API FACADE V59.0 (EXPLICIT FORENSIC EXPORT • ZERO TS COLLISIONS)

export * from './apiClient';
export * from './authService';
export * from './caseService';
export { forensicService, ForensicService } from './forensicService';
export * from './financeService';
export * from './archiveService';
export * from './calendarService';
export * from './chatService';
export * from './adminService';
export * from './lawService';

import { apiClient, setGlobalLogoutHandler } from './apiClient';
import { authService } from './authService';
import { caseService } from './caseService';
import { forensicService } from './forensicService';
import { financeService } from './financeService';
import { archiveService } from './archiveService';
import { calendarService } from './calendarService';
import { chatService } from './chatService';
import { adminService } from './adminService';
import { lawService } from './lawService';

class ApiService {
  public axiosInstance = apiClient;

  public setLogoutHandler(handler: () => void) {
    setGlobalLogoutHandler(handler);
  }

  // Auth Methods
  public setToken = authService.setToken.bind(authService);
  public getToken = authService.getToken.bind(authService);
  public refreshToken = authService.refreshToken.bind(authService);
  public login = authService.login.bind(authService);
  public logout = authService.logout.bind(authService);
  public register = authService.register.bind(authService);
  public fetchUserProfile = authService.fetchUserProfile.bind(authService);
  public changePassword = authService.changePassword.bind(authService);
  public deleteAccount = authService.deleteAccount.bind(authService);
  public forgotPassword = authService.forgotPassword.bind(authService);
  public resetPassword = authService.resetPassword.bind(authService);

  // Case Methods (Core CRUD & Records)
  public getCases = caseService.getCases.bind(caseService);
  public createCase = caseService.createCase.bind(caseService);
  public getCaseDetails = caseService.getCaseDetails.bind(caseService);
  public deleteCase = caseService.deleteCase.bind(caseService);
  public updateCasePosition = caseService.updateCasePosition.bind(caseService);
  public getDocuments = caseService.getDocuments.bind(caseService);
  public uploadDocument = caseService.uploadDocument.bind(caseService);
  public getDocument = caseService.getDocument.bind(caseService);
  public deleteDocument = caseService.deleteDocument.bind(caseService);
  public bulkDeleteDocuments = caseService.bulkDeleteDocuments.bind(caseService);
  public importArchiveDocuments = caseService.importArchiveDocuments.bind(caseService);
  public getDocumentContent = caseService.getDocumentContent.bind(caseService);
  public getOriginalDocument = caseService.getOriginalDocument.bind(caseService);
  public getPreviewDocument = caseService.getPreviewDocument.bind(caseService);
  public downloadDocumentReport = caseService.downloadDocumentReport.bind(caseService);
  public downloadObjection = caseService.downloadObjection.bind(caseService);
  public archiveCaseDocument = caseService.archiveCaseDocument.bind(caseService);
  public renameDocument = caseService.renameDocument.bind(caseService);
  public reprocessDocument = caseService.reprocessDocument.bind(caseService);
  public reprocessCaseDocuments = caseService.reprocessCaseDocuments.bind(caseService);
  public getCaseGraph = caseService.getCaseGraph.bind(caseService);
  public rebuildCaseGraph = caseService.rebuildCaseGraph.bind(caseService);
  public searchFirmGraph = caseService.searchFirmGraph.bind(caseService);
  public mergeGraphNodes = caseService.mergeGraphNodes.bind(caseService);
  public createCustomGraphEdge = caseService.createCustomGraphEdge.bind(caseService);
  public downloadCourtGraphReport = caseService.downloadCourtGraphReport.bind(caseService);
  public createMobileUploadSession = caseService.createMobileUploadSession.bind(caseService);
  public analyzeScannedImage = caseService.analyzeScannedImage.bind(caseService);
  public checkMobileUploadStatus = caseService.checkMobileUploadStatus.bind(caseService);
  public getMobileSessionFile = caseService.getMobileSessionFile.bind(caseService);
  public publicMobileUpload = caseService.publicMobileUpload.bind(caseService);
  public fetchImageBlob = caseService.fetchImageBlob.bind(caseService);
  public analyzeSpreadsheet = caseService.analyzeSpreadsheet.bind(caseService);
  public analyzeExistingSpreadsheet = caseService.analyzeExistingSpreadsheet.bind(caseService);
  public interrogateFinancialRecords = caseService.interrogateFinancialRecords.bind(caseService);

  // 🏛️ Forensic & Comprehensive Analysis Methods (Delegated to Isolated ForensicService)
  public analyzeCase = forensicService.analyzeCase.bind(forensicService);
  public clearCaseAnalysis = forensicService.clearCaseAnalysis.bind(forensicService);
  public archiveForensicReport = forensicService.archiveForensicReport.bind(forensicService);
  public downloadForensicReport = forensicService.downloadForensicReport.bind(forensicService);
  public clearDocumentAudit = forensicService.clearDocumentAudit.bind(forensicService);
  public crossExamineDocument = forensicService.crossExamineDocument.bind(forensicService);
  public analyzeDeepStrategy = forensicService.analyzeDeepStrategy.bind(forensicService);
  public analyzeDeepSimulation = forensicService.analyzeDeepSimulation.bind(forensicService);
  public analyzeDeepChronology = forensicService.analyzeDeepChronology.bind(forensicService);
  public analyzeDeepContradictions = forensicService.analyzeDeepContradictions.bind(forensicService);
  public archiveStrategyReport = forensicService.archiveStrategyReport.bind(forensicService);
  public forensicAnalyzeSpreadsheet = forensicService.forensicAnalyzeSpreadsheet.bind(forensicService);
  public forensicInterrogateEvidence = forensicService.forensicInterrogateEvidence.bind(forensicService);

  // Finance Methods
  public getInvoices = financeService.getInvoices.bind(financeService);
  public createInvoice = financeService.createInvoice.bind(financeService);
  public updateInvoice = financeService.updateInvoice.bind(financeService);
  public updateInvoiceStatus = financeService.updateInvoiceStatus.bind(financeService);
  public deleteInvoice = financeService.deleteInvoice.bind(financeService);
  public downloadInvoicePdf = financeService.downloadInvoicePdf.bind(financeService);
  public getInvoicePdfBlob = financeService.getInvoicePdfBlob.bind(financeService);
  public archiveInvoice = financeService.archiveInvoice.bind(financeService);
  public getExpenses = financeService.getExpenses.bind(financeService);
  public createExpense = financeService.createExpense.bind(financeService);
  public updateExpense = financeService.updateExpense.bind(financeService);
  public deleteExpense = financeService.deleteExpense.bind(financeService);
  public uploadExpenseReceipt = financeService.uploadExpenseReceipt.bind(financeService);
  public analyzeExpenseReceipt = financeService.analyzeExpenseReceipt.bind(financeService);
  public getExpenseReceiptBlob = financeService.getExpenseReceiptBlob.bind(financeService);
  public getBusinessProfile = financeService.getBusinessProfile.bind(financeService);
  public updateBusinessProfile = financeService.updateBusinessProfile.bind(financeService);
  public uploadBusinessLogo = financeService.uploadBusinessLogo.bind(financeService);
  public getWizardState = financeService.getWizardState.bind(financeService);
  public downloadMonthlyReport = financeService.downloadMonthlyReport.bind(financeService);
  public getAnalyticsDashboard = financeService.getAnalyticsDashboard.bind(financeService);
  public getCaseSummaries = financeService.getCaseSummaries.bind(financeService);

  // Archive Methods
  public getArchiveItems = archiveService.getArchiveItems.bind(archiveService);
  public createArchiveFolder = archiveService.createArchiveFolder.bind(archiveService);
  public uploadArchiveItem = archiveService.uploadArchiveItem.bind(archiveService);
  public deleteArchiveItem = archiveService.deleteArchiveItem.bind(archiveService);
  public renameArchiveItem = archiveService.renameArchiveItem.bind(archiveService);
  public shareDocument = archiveService.shareDocument.bind(archiveService);
  public shareArchiveItem = archiveService.shareArchiveItem.bind(archiveService);
  public shareArchiveCase = archiveService.shareArchiveCase.bind(archiveService);
  public downloadArchiveItem = archiveService.downloadArchiveItem.bind(archiveService);
  public getArchiveFileBlob = archiveService.getArchiveFileBlob.bind(archiveService);

  // Calendar Methods
  public getCalendarEvents = calendarService.getCalendarEvents.bind(calendarService);
  public createCalendarEvent = calendarService.createCalendarEvent.bind(calendarService);
  public deleteCalendarEvent = calendarService.deleteCalendarEvent.bind(calendarService);
  public getBriefing = calendarService.getBriefing.bind(calendarService);
  public getAlertsCount = calendarService.getAlertsCount.bind(calendarService);

  // Chat & Drafting Methods
  public submitChatFeedback = chatService.submitChatFeedback.bind(chatService);
  public clearChatHistory = chatService.clearChatHistory.bind(chatService);
  public updateChatHistory = chatService.updateChatHistory.bind(chatService);
  public getWebSocketUrl = chatService.getWebSocketUrl.bind(chatService);
  public initiateDraftingJob = chatService.initiateDraftingJob.bind(chatService);
  public getDraftingJobStatus = chatService.getDraftingJobStatus.bind(chatService);
  public getDraftingJobResult = chatService.getDraftingJobResult.bind(chatService);
  public sendChatMessageStream = chatService.sendChatMessageStream.bind(chatService);
  public draftLegalDocumentStream = chatService.draftLegalDocumentStream.bind(chatService);

  // Admin & Org Methods
  public getOrganizations = adminService.getOrganizations.bind(adminService);
  public getOrganization = adminService.getOrganization.bind(adminService);
  public upgradeOrganizationTier = adminService.upgradeOrganizationTier.bind(adminService);
  public getOrganizationMembers = adminService.getOrganizationMembers.bind(adminService);
  public inviteMember = adminService.inviteMember.bind(adminService);
  public acceptInvite = adminService.acceptInvite.bind(adminService);
  public removeOrganizationMember = adminService.removeOrganizationMember.bind(adminService);
  public getAllUsers = adminService.getAllUsers.bind(adminService);
  public updateUser = adminService.updateUser.bind(adminService);
  public deleteUser = adminService.deleteUser.bind(adminService);
  public updateSubscription = adminService.updateSubscription.bind(adminService);
  public promoteToFirm = adminService.promoteToFirm.bind(adminService);
  public getSupportMessages = adminService.getSupportMessages.bind(adminService);
  public sendSupportReply = adminService.sendSupportReply.bind(adminService);
  public sendContactForm = adminService.sendContactForm.bind(adminService);

  // Laws Methods
  public getLawArticle = lawService.getLawArticle.bind(lawService);
  public getCachedLawAnalysis = lawService.getCachedLawAnalysis.bind(lawService);
  public clearLawCache = lawService.clearLawCache.bind(lawService);
  public getLawArticlesByTitle = lawService.getLawArticlesByTitle.bind(lawService);
  public getLawTitles = lawService.getLawTitles.bind(lawService);
  public searchLaws = lawService.searchLaws.bind(lawService);
  public getLawByChunkId = lawService.getLawByChunkId.bind(lawService);
  public explainLawStream = lawService.explainLawStream.bind(lawService);
  public askLawAuditor = lawService.askLawAuditor.bind(lawService);
}

export const apiService = new ApiService();