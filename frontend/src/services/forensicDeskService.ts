// FILE: frontend/src/services/forensicDeskService.ts
// PHOENIX PROTOCOL - FORENSIC DEDICATED DESK CLIENT V4.0 (WAR ROOM COMPLETELY WIPED OUT)
// 100% COMPLETE CODE • ZERO CLIENT DEPENDENCY • ZERO TS WARNINGS • LEAN ARCHITECTURE

import { apiClient, API_V1_URL, tokenManager } from './apiClient';

export interface CustodyStamp {
  custody_hash: string;
  sealed_at: string;
  sealed_by_user_id: string;
  action: string;
  algorithm: string;
  evidence_ids: string[];
  is_verified: boolean;
  metadata?: Record<string, any>;
}

export interface ForensicDossier {
  id: string;
  caseNumber: string;
  title: string;
  clientName: string;
  clientPhone?: string;
  clientEmail?: string;
  courtJurisdiction: string;
  partnerLawyerName: string;
  partnerLawyerLicense: string;
  createdAt: string;
  updatedAt?: string;
  chainOfCustodyHash: string;
  isSealed: boolean;
  status: 'ACTIVE' | 'ARCHIVED' | 'DISPATCHED';
}

export interface ForensicMediaItem {
  id: string;
  _id?: string;
  case_id: string;
  owner_id: string;
  file_name: string;
  storage_key: string;
  media_type: 'audio' | 'video' | 'image';
  mime_type: string;
  status: string;
  evidence_sha256?: string;
  custody_stamp?: CustodyStamp;
  created_at: string;
}

export interface ForensicDocItem {
  id: string;
  _id?: string;
  case_id: string;
  owner_id: string;
  file_name: string;
  storage_key: string;
  mime_type: string;
  status: string;
  extracted_text?: string;
  evidence_sha256?: string;
  custody_stamp?: CustodyStamp;
  forensic_pillars?: Record<string, string>;
  media_type?: 'audio' | 'video' | 'image';
  media_id?: string;
  created_at: string;
}

export interface LabEvidenceCounts {
  DOCUMENTS: number;
  AUDIO: number;
  VISUAL: number;
  FINANCIAL: number;
}

export interface AudioAnalysisResponse {
  formatted_transcript: string;
  segments: Array<{
    speaker: string;
    start: number;
    end: number;
    timestamp_label: string;
    text: string;
  }>;
  stress_flags: Array<{
    start: number;
    end: number;
    text: string;
    intensity: string;
    confidence: number;
  }>;
  forensic_intelligence: {
    summary: string;
    threat_level: string;
    criminal_elements_detected: string[];
    stress_and_intimidation_analysis: string;
    contradictions_found: string[];
    court_admissibility_recommendation: string;
  };
}

export interface VisualAnalysisResponse {
  exif_metadata: {
    camera_make?: string;
    camera_model?: string;
    software_used?: string;
    original_date?: string;
    has_gps: boolean;
    latitude?: number;
    longitude?: number;
    google_maps_url?: string;
  };
  tamper_analysis: {
    manipulation_risk_score: number;
    is_suspicious: boolean;
    verdict: string;
  };
  vision_detection: {
    objects: Array<{ name: string; score: number }>;
    labels: Array<{ description: string; score: number }>;
    text_detected: string;
  };
  forensic_opinion: {
    authenticity_assessment: string;
    key_findings: string[];
    chain_of_custody_impact: string;
    court_defense_strategy: string;
    expert_statement: string;
  };
}

export interface CCTVVideoAnalysisResponse {
  keyframes_count: number;
  keyframes_summary: Array<{ timestamp: string; tamper_score: number }>;
  avg_tamper_score: number;
  is_manipulated: boolean;
  detected_entities: string[];
  forensic_report: {
    cctv_chronology: Array<{ timestamp: string; description: string }>;
    tamper_verdict: string;
    key_identifications: string[];
    alibi_impact_assessment: string;
    court_admissibility_statement: string;
    expert_summary: string;
  };
  analyzed_at: string;
}

export interface LMDInterestResponse {
  principal: number;
  interest_rate_annual: number;
  start_date: string;
  end_date: string;
  days_elapsed: number;
  daily_accrual: number;
  interest_amount: number;
  total_obligation: number;
  legal_basis: string;
}

export class ForensicDeskService {
  private readonly baseUrl = '/forensic';

  // ==========================================================
  // 1. DOSJET FORENZIKE DHE VULOSJA SERVER-SIDE
  // ==========================================================
  public async loadAllDossiers(): Promise<{ rawCases: any[]; mappedDossiers: ForensicDossier[] }> {
    try {
      const response = await apiClient.get<any[]>(`${this.baseUrl}/dossiers`);
      const dossiers = response.data || [];

      const mapped: ForensicDossier[] = dossiers.map((d: any) => {
        const custodyArr = d.chain_of_custody || [];
        const latestStamp = custodyArr.length > 0 ? custodyArr[custodyArr.length - 1] : null;
        const hash = latestStamp ? latestStamp.custody_hash : `SEAL-${d._id?.slice(-8).toUpperCase()}`;

        return {
          id: d._id || d.id,
          caseNumber: d.case_number || `FOR-${(d._id || '').slice(-6).toUpperCase()}`,
          title: d.title || 'Dosje pa titull',
          clientName: d.client_name || d.title?.replace(/^DOSJA FORENZIKE:\s*/i, '') || 'Palë e Regjistruar',
          clientPhone: d.client_phone,
          clientEmail: d.client_email,
          courtJurisdiction: d.court_jurisdiction || 'Gjykata Themelore Prishtinë',
          partnerLawyerName: 'Avokatura Forenzike',
          partnerLawyerLicense: 'OAK-KS',
          createdAt: d.created_at || new Date().toISOString(),
          updatedAt: d.updated_at,
          chainOfCustodyHash: hash,
          isSealed: !!d.is_sealed,
          status: 'ACTIVE'
        };
      });

      return { rawCases: dossiers, mappedDossiers: mapped };
    } catch (err) {
      console.error("Dështoi leximi nga /forensic/dossiers:", err);
      return { rawCases: [], mappedDossiers: [] };
    }
  }

  public async createDossier(payload: {
    clientName: string;
    caseNumber?: string;
    courtJurisdiction?: string;
    caseSummary?: string;
  }): Promise<ForensicDossier> {
    const body = {
      title: `DOSJA FORENZIKE: ${payload.clientName}`,
      case_number: payload.caseNumber,
      court_jurisdiction: payload.courtJurisdiction || 'Gjykata Themelore Prishtinë',
      case_summary: payload.caseSummary || ''
    };

    const response = await apiClient.post<any>(`${this.baseUrl}/dossiers`, body);
    const d = response.data;
    const custodyArr = d.chain_of_custody || [];
    const latestStamp = custodyArr.length > 0 ? custodyArr[custodyArr.length - 1] : null;

    return {
      id: d._id,
      caseNumber: d.case_number,
      title: d.title,
      clientName: payload.clientName,
      courtJurisdiction: d.court_jurisdiction,
      partnerLawyerName: 'Avokatura Forenzike',
      partnerLawyerLicense: 'OAK-KS',
      createdAt: d.created_at,
      chainOfCustodyHash: latestStamp ? latestStamp.custody_hash : 'PENDING_SEAL',
      isSealed: !!d.is_sealed,
      status: 'ACTIVE'
    };
  }

  public async sealCustody(caseId: string, actionNote: string, evidenceIds: string[] = []): Promise<CustodyStamp> {
    const response = await apiClient.post<{ success: boolean; custody_stamp: CustodyStamp }>(
      `${this.baseUrl}/dossiers/${caseId}/seal-custody`,
      { action_note: actionNote, evidence_ids: evidenceIds }
    );
    return response.data.custody_stamp;
  }

  public async getAuditTrail(caseId: string): Promise<any[]> {
    const response = await apiClient.get<{ trail: any[] }>(`${this.baseUrl}/dossiers/${caseId}/audit-trail`);
    return response.data.trail || [];
  }

  public async deleteDossier(caseId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/dossiers/${caseId}`);
  }

  // ==========================================================
  // 2. LABORATORI I AUDIOS
  // ==========================================================
  public async uploadForensicAudio(caseId: string, file: File): Promise<ForensicMediaItem> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('file', file);
    const response = await apiClient.post<ForensicMediaItem>(`${this.baseUrl}/audio/upload`, formData);
    return response.data;
  }

  public async listForensicAudio(caseId: string): Promise<ForensicMediaItem[]> {
    const response = await apiClient.get<ForensicMediaItem[]>(`${this.baseUrl}/audio/${caseId}/list`);
    return response.data || [];
  }

  public async deleteForensicAudio(caseId: string, mediaId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/audio/${caseId}/${mediaId}`);
  }

  public getForensicAudioStreamUrl(caseId: string, mediaId: string, token: string): string {
    return `${API_V1_URL}/forensic/audio/${caseId}/${mediaId}/stream?token=${encodeURIComponent(token)}`;
  }

  public async analyzeAudioLab(caseId: string, file: File, caseContext: string = ''): Promise<AudioAnalysisResponse> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('case_context', caseContext);
    formData.append('file', file);

    const response = await apiClient.post<{ success: boolean; data: AudioAnalysisResponse }>(
      `${this.baseUrl}/audio/analyze`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data.data;
  }

  public async getPureAudioTranscript(caseId: string, file: File): Promise<string> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('file', file);

    const response = await apiClient.post<{ success: boolean; data: string }>(
      `${this.baseUrl}/audio/pure-transcript`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data.data;
  }

  // ==========================================================
  // 3. LABORATORI VIZUAL DHE CCTV VIDEO
  // ==========================================================
  public async uploadForensicVisual(caseId: string, file: File): Promise<ForensicMediaItem> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('file', file);
    const response = await apiClient.post<ForensicMediaItem>(`${this.baseUrl}/visual/upload`, formData);
    return response.data;
  }

  public async listForensicVisual(caseId: string): Promise<ForensicMediaItem[]> {
    const response = await apiClient.get<ForensicMediaItem[]>(`${this.baseUrl}/visual/${caseId}/list`);
    return response.data || [];
  }

  public async deleteForensicVisual(caseId: string, mediaId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/visual/${caseId}/${mediaId}`);
  }

  public getForensicVisualStreamUrl(caseId: string, mediaId: string, token: string): string {
    return `${API_V1_URL}/forensic/visual/${caseId}/${mediaId}/stream?token=${encodeURIComponent(token)}`;
  }

  public async analyzeVisualLab(caseId: string, file: File, caseContext: string = ''): Promise<VisualAnalysisResponse> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('case_context', caseContext);
    formData.append('file', file);

    const response = await apiClient.post<{ success: boolean; data: VisualAnalysisResponse }>(
      `${this.baseUrl}/visual/analyze`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data.data;
  }

  public async analyzeForensicVideo(caseId: string, file: File, caseContext: string = ''): Promise<CCTVVideoAnalysisResponse> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('case_context', caseContext);
    formData.append('file', file);

    const response = await apiClient.post<{ success: boolean; data: CCTVVideoAnalysisResponse }>(
      `${this.baseUrl}/visual/analyze-video`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data.data;
  }

  // ==========================================================
  // 4. LABORATORI I SHKRESAVE DHE SHTJELLAVE
  // ==========================================================
  public async uploadForensicDocument(caseId: string, file: File): Promise<ForensicDocItem> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    formData.append('file', file);
    const response = await apiClient.post<ForensicDocItem>(`${this.baseUrl}/documents/upload`, formData);
    return response.data;
  }

  public async listForensicDocuments(caseId: string): Promise<ForensicDocItem[]> {
    const response = await apiClient.get<ForensicDocItem[]>(`${this.baseUrl}/documents/${caseId}/list`);
    return response.data || [];
  }

  public async deleteForensicDocument(caseId: string, docId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/documents/${caseId}/${docId}`);
  }

  public async renameForensicDocument(caseId: string, docId: string, newName: string): Promise<void> {
    await apiClient.put(`${this.baseUrl}/documents/${caseId}/${docId}/rename`, { new_name: newName });
  }

  public async getForensicDocPillars(caseId: string, docId: string): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>(`${this.baseUrl}/documents/${caseId}/${docId}/pillars`);
    return response.data || {};
  }

  public async generateForensicDocPillar(caseId: string, docId: string, pillar: string, prompt: string): Promise<string> {
    const response = await apiClient.post<{ content: string }>(
      `${this.baseUrl}/documents/${caseId}/${docId}/pillars`,
      { pillar, prompt }
    );
    return response.data.content || '';
  }

  public async deleteForensicDocPillar(caseId: string, docId: string, pillar: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/documents/${caseId}/${docId}/pillars/${pillar}`);
  }

  public async saveForensicDocPillarContent(
    caseId: string,
    docId: string,
    pillar: string,
    content: string
  ): Promise<void> {
    await apiClient.put(`${this.baseUrl}/documents/${caseId}/${docId}/pillars/${pillar}`, { content });
  }

  public async getForensicCasePillars(caseId: string): Promise<Record<string, string>> {
    const response = await apiClient.get<Record<string, string>>(`${this.baseUrl}/dossiers/${caseId}/pillars`);
    return response.data || {};
  }

  public async saveForensicCasePillarContent(
    caseId: string,
    pillar: string,
    content: string
  ): Promise<void> {
    await apiClient.put(`${this.baseUrl}/dossiers/${caseId}/pillars/${pillar}`, { content });
  }

  public async deleteForensicCasePillar(caseId: string, pillar: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/dossiers/${caseId}/pillars/${pillar}`);
  }

  // ==========================================================
  // 5. LABORATORI FINANCIAR (LMD 265 & PANDAS)
  // ==========================================================
  public async calculateLegalInterest(params: {
    principal: number;
    startDate: string;
    endDate?: string;
    ratePercent?: number;
    caseId?: string;
  }): Promise<LMDInterestResponse> {
    const response = await apiClient.post<{ success: boolean; data: LMDInterestResponse }>(
      `${this.baseUrl}/finance/calculate-interest`,
      {
        principal: params.principal,
        start_date: params.startDate,
        end_date: params.endDate,
        rate_percent: params.ratePercent ?? 8.0,
        case_id: params.caseId
      }
    );
    return response.data.data;
  }

  public async getFinancialRecords(caseId: string): Promise<any[]> {
    const response = await apiClient.get<{ records: any[] }>(`${this.baseUrl}/finance/${caseId}/records`);
    return response.data.records || [];
  }

  public async analyzeSpreadsheet(
    caseId: string,
    file: File,
    claimedAmount?: number,
    caseContext: string = ''
  ): Promise<any> {
    const formData = new FormData();
    formData.append('case_id', caseId);
    if (claimedAmount !== undefined && claimedAmount !== null) {
      formData.append('claimed_amount', claimedAmount.toString());
    }
    formData.append('case_context', caseContext);
    formData.append('file', file);

    const response = await apiClient.post<any>(
      `${this.baseUrl}/finance/analyze-spreadsheet`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }

  // ==========================================================
  // 6. TERMINALI FORENZIK ME KUJTESË DHE STREAMING
  // ==========================================================
  public async sendChatMessage(caseId: string, message: string, caseContext: string = ''): Promise<any> {
    const response = await apiClient.post<any>(`${this.baseUrl}/chat`, {
      case_id: caseId,
      message,
      case_context: caseContext
    });
    return response.data;
  }

  public async streamForensicChat(
    caseId: string,
    message: string,
    caseContext: string = ''
  ): Promise<ReadableStream<Uint8Array>> {
    const token = tokenManager.get();
    if (!token) {
      throw new Error('Token mungon. Ju lutemi kyçuni përsëri.');
    }

    const response = await fetch(`${API_V1_URL}/forensic/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        case_id: caseId,
        message,
        case_context: caseContext
      })
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || 'Dështoi lidhja me serverin për streaming.');
    }

    if (!response.body) {
      throw new Error('Streaming nuk u ofrua nga serveri.');
    }

    return response.body;
  }

  public async getChatHistory(caseId: string): Promise<any[]> {
    const response = await apiClient.get<{ messages: any[] }>(`${this.baseUrl}/chat/${caseId}/history`);
    return response.data.messages || [];
  }

  public async clearChatHistory(caseId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/chat/${caseId}`);
  }

  // ==========================================================
  // STATISTIKAT E PROVAVE (VETËM LABORATORËT REALË TË PROVAVE)
  // ==========================================================
  public async getEvidenceCounts(caseId: string): Promise<LabEvidenceCounts> {
    try {
      const [audios, visuals, docs] = await Promise.all([
        this.listForensicAudio(caseId).catch(() => []),
        this.listForensicVisual(caseId).catch(() => []),
        this.listForensicDocuments(caseId).catch(() => [])
      ]);

      return {
        DOCUMENTS: docs.length,
        AUDIO: audios.length,
        VISUAL: visuals.length,
        FINANCIAL: docs.length > 0 ? 1 : 0
      };
    } catch {
      return { DOCUMENTS: 0, AUDIO: 0, VISUAL: 0, FINANCIAL: 0 };
    }
  }
}

export const forensicDeskService = new ForensicDeskService();