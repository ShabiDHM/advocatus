// FILE: src/services/financeService.ts
// PHOENIX PROTOCOL - INVOICES, EXPENSES & FINANCIAL ANALYTICS SERVICE MODULE

import { apiClient } from './apiClient';
import type {
  Invoice,
  InvoiceCreateRequest,
  InvoiceItem,
  Expense,
  ExpenseCreateRequest,
  ExpenseUpdate,
  BusinessProfile,
  BusinessProfileUpdate,
  CaseFinancialSummary,
  AnalyticsDashboardData,
  ArchiveItemOut
} from '../data/types';

export interface AuditIssue { id: string; severity: 'CRITICAL' | 'WARNING'; message: string; related_item_id?: string; item_type?: 'INVOICE' | 'EXPENSE'; }
export interface TaxCalculation { period_month: number; period_year: number; total_sales_gross: number; total_purchases_gross: number; vat_collected: number; vat_deductible: number; net_obligation: number; currency: string; status: string; regime: string; taxation_rate_applied: string; description: string; }
export interface WizardState { calculation: TaxCalculation; issues: AuditIssue[]; ready_to_close: boolean; }
export interface InvoiceUpdate { client_name?: string; client_email?: string; client_address?: string; items?: InvoiceItem[]; tax_rate?: number; due_date?: string; status?: string; notes?: string; }
export interface ReceiptAnalysisResult { category: string; amount: number; date: string; description: string; }

export class FinanceService {
  // ========== INVOICES ==========
  public async getInvoices(): Promise<Invoice[]> {
    const response = await apiClient.get<any>('/finance/invoices');
    return Array.isArray(response.data) ? response.data : (response.data.invoices || []);
  }

  public async createInvoice(data: InvoiceCreateRequest): Promise<Invoice> {
    const response = await apiClient.post<Invoice>('/finance/invoices', data);
    return response.data;
  }

  public async updateInvoice(invoiceId: string, data: InvoiceUpdate): Promise<Invoice> {
    const response = await apiClient.put<Invoice>(`/finance/invoices/${invoiceId}`, data);
    return response.data;
  }

  public async updateInvoiceStatus(invoiceId: string, status: string): Promise<Invoice> {
    const response = await apiClient.put<Invoice>(`/finance/invoices/${invoiceId}/status`, { status });
    return response.data;
  }

  public async deleteInvoice(invoiceId: string): Promise<void> {
    await apiClient.delete(`/finance/invoices/${invoiceId}`);
  }

  public async downloadInvoicePdf(invoiceId: string, lang: string = 'sq'): Promise<void> {
    const response = await apiClient.get(`/finance/invoices/${invoiceId}/pdf`, { params: { lang }, responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Invoice_${invoiceId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  public async getInvoicePdfBlob(invoiceId: string, lang: string = 'sq'): Promise<Blob> {
    const response = await apiClient.get(`/finance/invoices/${invoiceId}/pdf`, { params: { lang }, responseType: 'blob' });
    return response.data;
  }

  public async archiveInvoice(invoiceId: string, caseId?: string): Promise<ArchiveItemOut> {
    const params = caseId ? { case_id: caseId } : {};
    const response = await apiClient.post<ArchiveItemOut>(`/finance/invoices/${invoiceId}/archive`, null, { params });
    return response.data;
  }

  // ========== EXPENSES ==========
  public async getExpenses(): Promise<Expense[]> {
    const response = await apiClient.get<any>('/finance/expenses');
    return Array.isArray(response.data) ? response.data : (response.data.invoices || []);
  }

  public async createExpense(data: ExpenseCreateRequest): Promise<Expense> {
    const response = await apiClient.post<Expense>('/finance/expenses', data);
    return response.data;
  }

  public async updateExpense(expenseId: string, data: ExpenseUpdate): Promise<Expense> {
    const response = await apiClient.put<Expense>(`/finance/expenses/${expenseId}`, data);
    return response.data;
  }

  public async deleteExpense(expenseId: string): Promise<void> {
    await apiClient.delete(`/finance/expenses/${expenseId}`);
  }

  public async uploadExpenseReceipt(expenseId: string, file: File): Promise<void> {
    const formData = new FormData();
    formData.append('file', file);
    await apiClient.put(`/finance/expenses/${expenseId}/receipt`, formData);
  }

  public async analyzeExpenseReceipt(file: File): Promise<ReceiptAnalysisResult> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<ReceiptAnalysisResult>('/finance/expenses/analyze-receipt', formData);
    return response.data;
  }

  public async getExpenseReceiptBlob(expenseId: string): Promise<{ blob: Blob; filename: string }> {
    const response = await apiClient.get(`/finance/expenses/${expenseId}/receipt`, { responseType: 'blob' });
    const disposition = response.headers['content-disposition'];
    let filename = `receipt-${expenseId}.pdf`;
    if (disposition && disposition.indexOf('filename=') !== -1) {
      const matches = /filename="([^"]*)"/.exec(disposition);
      if (matches != null && matches[1]) filename = matches[1];
    }
    return { blob: response.data, filename };
  }

  // ========== BUSINESS PROFILE ==========
  public async getBusinessProfile(): Promise<BusinessProfile> {
    const response = await apiClient.get<BusinessProfile>('/business/profile');
    return response.data;
  }

  public async updateBusinessProfile(data: BusinessProfileUpdate): Promise<BusinessProfile> {
    const response = await apiClient.put<BusinessProfile>('/business/profile', data);
    return response.data;
  }

  public async uploadBusinessLogo(file: File): Promise<BusinessProfile> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.put<BusinessProfile>('/business/logo', formData);
    return response.data;
  }

  // ========== WIZARD & ANALYTICS ==========
  public async getWizardState(month: number, year: number): Promise<WizardState> {
    const response = await apiClient.get<WizardState>('/finance/wizard/state', { params: { month, year } });
    return response.data;
  }

  public async downloadMonthlyReport(month: number, year: number): Promise<void> {
    const response = await apiClient.get('/finance/wizard/report/pdf', { params: { month, year }, responseType: 'blob' });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `Raporti_${month}_${year}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  public async getAnalyticsDashboard(days: number = 30): Promise<AnalyticsDashboardData> {
    const response = await apiClient.get<AnalyticsDashboardData>('/finance/analytics/dashboard', { params: { days } });
    return response.data;
  }

  public async getCaseSummaries(): Promise<CaseFinancialSummary[]> {
    const response = await apiClient.get<CaseFinancialSummary[]>('/finance/case-summary');
    return response.data;
  }
}

export const financeService = new FinanceService();