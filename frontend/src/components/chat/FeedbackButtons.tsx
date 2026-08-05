// FILE: src/components/chat/FeedbackButtons.tsx
import React, { useState } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { apiService } from '../../services/api';

interface FeedbackButtonsProps {
  messageIndex: number;
  caseId: string;
  onFeedback: (index: number, feedback: 'up' | 'down') => void;
  disabled?: boolean;
}

export const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({
  messageIndex,
  caseId,
  onFeedback,
  disabled,
}) => {
  const [submitting, setSubmitting] = useState<'up' | 'down' | null>(null);
  const [success, setSuccess] = useState(false);

  const handleFeedback = async (feedback: 'up' | 'down') => {
    if (submitting || disabled) return;
    setSubmitting(feedback);
    try {
      await apiService.submitChatFeedback(caseId, messageIndex, feedback);
      setSuccess(true);
      onFeedback(messageIndex, feedback);
      setTimeout(() => setSuccess(false), 2000);
    } catch (error) {
      console.error('Feedback failed:', error);
    } finally {
      setSubmitting(null);
    }
  };

  return (
    <div className="flex items-center gap-2 mt-2 pt-2 border-t border-main">
      <button
        type="button"
        onClick={() => handleFeedback('up')}
        disabled={!!submitting || disabled || success}
        className={`p-1.5 rounded-lg transition-all border hover-lift shadow-sm focus:outline-none ${
          success
            ? 'bg-status-success/20 text-status-success border-status-success/30'
            : 'bg-surface text-text-muted border-main hover:text-status-success hover:border-status-success/50'
        }`}
        title="Përgjigje e dobishme"
      >
        {submitting === 'up' ? (
          <span className="w-3.5 h-3.5 border-2 border-t-transparent border-current rounded-full animate-spin block" />
        ) : (
          <ThumbsUp size={12} />
        )}
      </button>
      <button
        type="button"
        onClick={() => handleFeedback('down')}
        disabled={!!submitting || disabled || success}
        className={`p-1.5 rounded-lg transition-all border hover-lift shadow-sm focus:outline-none ${
          success
            ? 'bg-status-success/20 text-status-success border-status-success/30'
            : 'bg-surface text-text-muted border-main hover:text-danger-start hover:border-danger-start/50'
        }`}
        title="Përgjigje e padobishme"
      >
        {submitting === 'down' ? (
          <span className="w-3.5 h-3.5 border-2 border-t-transparent border-current rounded-full animate-spin block" />
        ) : (
          <ThumbsDown size={12} />
        )}
      </button>
    </div>
  );
};