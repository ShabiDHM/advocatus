// FILE: src/utils/caseHelpers.ts
import { ChatMessage } from '../data/types';

export const safeString = (val: any): string => {
  if (!val) return '';
  if (typeof val === 'string') return val;
  try {
    return JSON.stringify(val);
  } catch {
    return String(val);
  }
};

export const extractAndNormalizeHistory = (data: any): ChatMessage[] => {
  if (!data) return [];
  const rawArray = data.chat_history || data.chatHistory || data.history || data.messages || [];
  if (!Array.isArray(rawArray)) return [];

  return rawArray
    .map((item: any) => {
      if (!item) return null;

      const rawRole = (item.role || item.sender || item.author || 'user').toString().toLowerCase();
      const role: 'user' | 'ai' =
        rawRole.includes('ai') || rawRole.includes('assistant') || rawRole.includes('system') ? 'ai' : 'user';

      let contentStr = '';
      if (typeof item.content === 'string') {
        contentStr = item.content;
      } else if (typeof item.message === 'string') {
        contentStr = item.message;
      } else if (typeof item.text === 'string') {
        contentStr = item.text;
      } else if (item.content && typeof item.content === 'object') {
        contentStr = item.content.text || item.content.message || JSON.stringify(item.content);
      } else {
        contentStr = safeString(item.content || item.message || item.text);
      }

      const timestamp = item.timestamp || item.created_at || new Date().toISOString();
      return { role, content: contentStr, timestamp };
    })
    .filter((msg): msg is ChatMessage => Boolean(msg && typeof msg.content === 'string' && msg.content.trim() !== ''));
};

export const getUserSalutation = (user: any): string => {
  if (!user) return 'Avokat';
  const rawName = (user.last_name || user.lastName || user.full_name || user.name || user.first_name || '').trim();
  const cleanName = rawName.replace(/[\(\)]/g, '').replace(/admin/gi, '').trim();

  if (!cleanName) return 'Avokat';
  const parts = cleanName.split(' ');
  const lastName = parts.length > 1 ? parts[parts.length - 1] : parts[0];

  return lastName ? `z. ${lastName}` : 'Avokat';
};