// FILE: src/services/calendarService.ts
// PHOENIX PROTOCOL - CALENDAR & DEADLINE ALERTS SERVICE MODULE V3.0 (VOICE PARSING)

import { apiClient } from './apiClient';
import type { CalendarEvent, CalendarEventCreateRequest, BriefingResponse } from '../data/types';

export interface VoiceParseResponse {
  success: boolean;
  parsed: {
    category?: 'AGENDA' | 'FACT';
    title?: string;
    description?: string;
    event_type?: string;
    priority?: string;
    start_date?: string;
    location?: string;
  };
}

export interface VoiceTranscribeResponse {
  success: boolean;
  transcription: string;
  parsed: {
    category?: 'AGENDA' | 'FACT';
    title?: string;
    description?: string;
    event_type?: string;
    priority?: string;
    start_date?: string;
    location?: string;
  };
}

export class CalendarService {
  public async getCalendarEvents(): Promise<CalendarEvent[]> {
    const response = await apiClient.get<CalendarEvent[]>('/calendar/events');
    return response.data;
  }

  public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> {
    const response = await apiClient.post<CalendarEvent>('/calendar/events', data);
    return response.data;
  }

  public async updateCalendarEvent(eventId: string, updates: Partial<CalendarEvent>): Promise<CalendarEvent> {
    const response = await apiClient.patch<CalendarEvent>(`/calendar/events/${eventId}`, updates);
    return response.data;
  }

  public async deleteCalendarEvent(eventId: string): Promise<void> {
    await apiClient.delete(`/calendar/events/${eventId}`);
  }

  public async getBriefing(): Promise<BriefingResponse> {
    const response = await apiClient.get<BriefingResponse>('/calendar/alerts');
    return response.data;
  }

  public async getAlertsCount(): Promise<{ count: number }> {
    const response = await this.getBriefing();
    return { count: response.count };
  }

  // ==========================================================
  // VOICE → EVENT METHODS
  // ==========================================================
  public async parseVoiceText(text: string): Promise<VoiceParseResponse> {
    const response = await apiClient.post<VoiceParseResponse>('/calendar/voice-parse', { text });
    return response.data;
  }

  public async transcribeVoiceAndParse(file: File): Promise<VoiceTranscribeResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<VoiceTranscribeResponse>(
      '/calendar/voice-transcribe',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  }
}

export const calendarService = new CalendarService();