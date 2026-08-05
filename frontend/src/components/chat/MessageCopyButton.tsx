// FILE: src/components/chat/MessageCopyButton.tsx
import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { extractFollowUpQuestions } from '../../utils/chatHelpers';

export const MessageCopyButton: React.FC<{ text: string }> = ({ text }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    try {
      const { cleanText } = extractFollowUpQuestions(text || '');
      await navigator.clipboard.writeText(cleanText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error(err);
    }
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      className={`absolute top-2 right-2 p-2 rounded-xl transition-all opacity-0 group-hover:opacity-100 shadow-sm hover-lift focus:outline-none ${
        copied
          ? 'bg-status-success/20 text-status-success'
          : 'bg-surface border border-main text-text-muted hover:text-primary-start'
      }`}
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
};