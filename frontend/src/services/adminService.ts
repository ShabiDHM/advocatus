// FILE: src/services/adminService.ts
// PHOENIX PROTOCOL - ADMIN, ORGANIZATIONS & SUPPORT SERVICE MODULE

import { apiClient } from './apiClient';
import type {
  Organization,
  User,
  UpdateUserRequest,
  AcceptInviteRequest,
  SubscriptionUpdate,
  PromoteRequest
} from '../data/types';

export class AdminService {
  public async getOrganizations(): Promise<Organization[]> {
    const response = await apiClient.get<Organization[]>('/admin/organizations');
    return response.data;
  }

  public async getOrganization(): Promise<Organization> {
    const response = await apiClient.get<Organization>('/organizations/me');
    return response.data;
  }

  public async upgradeOrganizationTier(orgId: string, tier: string): Promise<Organization> {
    const response = await apiClient.put<Organization>(`/admin/organizations/${orgId}/tier`, { tier });
    return response.data;
  }

  public async getOrganizationMembers(): Promise<User[]> {
    const response = await apiClient.get<User[]>('/organizations/members');
    return response.data;
  }

  public async inviteMember(email: string): Promise<any> {
    const response = await apiClient.post('/organizations/invite', { email });
    return response.data;
  }

  public async acceptInvite(data: AcceptInviteRequest): Promise<{ message: string }> {
    const response = await apiClient.post('/organizations/accept-invite', data);
    return response.data;
  }

  public async removeOrganizationMember(memberId: string): Promise<any> {
    const response = await apiClient.delete(`/organizations/members/${memberId}`);
    return response.data;
  }

  public async getAllUsers(): Promise<User[]> {
    const response = await apiClient.get<any>('/admin/users');
    return Array.isArray(response.data) ? response.data : (response.data.users || []);
  }

  public async updateUser(userId: string, data: UpdateUserRequest): Promise<User> {
    const response = await apiClient.put<User>(`/admin/users/${userId}`, data);
    return response.data;
  }

  public async deleteUser(userId: string): Promise<void> {
    await apiClient.delete(`/admin/users/${userId}`);
  }

  public async updateSubscription(userId: string, data: SubscriptionUpdate): Promise<{ message: string }> {
    const response = await apiClient.post(`/admin/users/${userId}/subscription`, data);
    return response.data;
  }

  public async promoteToFirm(userId: string, data: PromoteRequest): Promise<{ message: string }> {
    const response = await apiClient.post(`/admin/users/${userId}/promote`, data);
    return response.data;
  }

  public async getSupportMessages(): Promise<any[]> {
    const response = await apiClient.get('/support/messages');
    return response.data;
  }

  public async sendSupportReply(toEmail: string, replyMessage: string, ticketId?: string): Promise<any> {
    const response = await apiClient.post('/support/reply', {
      to_email: toEmail,
      reply_message: replyMessage,
      ticket_id: ticketId,
    });
    return response.data;
  }

  public async sendContactForm(data: { firstName: string; lastName: string; email: string; phone: string; message: string }): Promise<void> {
    await apiClient.post('/support/contact', {
      first_name: data.firstName,
      last_name: data.lastName,
      email: data.email,
      phone: data.phone,
      message: data.message,
    });
  }
}

export const adminService = new AdminService();