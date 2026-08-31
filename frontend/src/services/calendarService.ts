// FILE: src/services/calendarService.ts
// PHOENIX PROTOCOL - CALENDAR & DEADLINE ALERTS SERVICE MODULE

import { apiClient } from './apiClient';
import type { CalendarEvent, CalendarEventCreateRequest, BriefingResponse } from '../data/types';

export class CalendarService {
  public async getCalendarEvents(): Promise<CalendarEvent[]> {
    const response = await apiClient.get<CalendarEvent[]>('/calendar/events');
    return response.data;
  }

  public async createCalendarEvent(data: CalendarEventCreateRequest): Promise<CalendarEvent> {
    const response = await apiClient.post<CalendarEvent>('/calendar/events', data);
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
}

export const calendarService = new CalendarService();