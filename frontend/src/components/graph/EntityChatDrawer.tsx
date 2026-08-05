// FILE: src/components/graph/EntityChatDrawer.tsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bot, X, Info, ChevronRight, Loader2, Send } from 'lucide-react';
import { OntologyNode, ChatMsg, ENTITY_CONFIG } from './graphTypes';
import { translateToAlbanian } from '../../utils/albanianLegalTranslator';
import { LawCitationText } from '../LawCitationText';

interface EntityChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  chatEntity: OntologyNode | null;
  clientPosition: 'DEFENDANT' | 'PLAINTIFF' | 'NEUTRAL';
  entityMessages: ChatMsg[];
  inputQuestion: string;
  onInputChange: (val: string) => void;
  isSending: boolean;
  onSendQuestion: (customPrompt?: string) => void;
  suggestedCards: Array<{ badge: string; title: string; desc: string; query: string; icon: any }>;
  chatScrollRef: React.Ref<HTMLDivElement>;
}

export const EntityChatDrawer: React.FC<EntityChatDrawerProps> = ({
  isOpen,
  onClose,
  chatEntity,
  clientPosition,
  entityMessages,
  inputQuestion,
  onInputChange,
  isSending,
  onSendQuestion,
  suggestedCards,
  chatScrollRef,
}) => {
  return (
    <AnimatePresence>
      {isOpen && chatEntity && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[250] flex items-center justify-end p-2 sm:p-4">
          <motion.div
            initial={{ x: 300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 300, opacity: 0 }}
            className="w-full max-w-lg h-[90vh] bg-canvas border border-main rounded-3xl shadow-2xl flex flex-col overflow-hidden"
          >
            <div className="p-4 sm:p-5 bg-surface border-b border-main flex items-center justify-between shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-start/10 text-primary-start rounded-xl flex items-center justify-center border border-primary-start/20">
                  <Bot size={20} />
                </div>
                <div>
                  <h3 className="text-sm font-black text-text-primary uppercase tracking-tight">
                    Hetimi AI: {translateToAlbanian(chatEntity.label)}
                  </h3>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] text-text-muted font-bold uppercase">
                      {ENTITY_CONFIG[chatEntity.type].albanianLabel}
                    </span>
                    <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded-full bg-indigo-500/15 text-indigo-400 border border-indigo-500/30">
                      {clientPosition === 'DEFENDANT'
                        ? '🛡️ Mandati: I Paditur (Mbrojtje)'
                        : clientPosition === 'PLAINTIFF'
                        ? '⚔️ Mandati: Paditësi (Sulm)'
                        : '⚖️ Mandati: Neutral'}
                    </span>
                  </div>
                </div>
              </div>
              <button type="button" onClick={onClose} className="p-2 text-text-muted hover:text-text-primary rounded-xl">
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 p-4 sm:p-5 overflow-y-auto custom-finance-scroll space-y-6">
              {entityMessages.length === 0 && (
                <div className="text-center space-y-3 pt-2">
                  <h2 className="text-base sm:text-lg font-black text-text-primary uppercase tracking-tight">
                    AGJENTI I HETIMIT: {translateToAlbanian(chatEntity.label)}
                  </h2>
                  <div className="p-2.5 bg-surface/60 border border-main rounded-xl text-[11px] text-text-muted inline-flex items-center gap-2 text-left">
                    <Info size={14} className="text-primary-start shrink-0" />
                    <span>Përgjigjet e AI shërbejnë për referencë dhe verifikohen nga avokati.</span>
                  </div>

                  <div className="grid grid-cols-1 gap-3 pt-4 text-left">
                    {suggestedCards.map((card, idx) => {
                      const CardIcon = card.icon;
                      return (
                        <div
                          key={idx}
                          onClick={() => onSendQuestion(card.query)}
                          className="p-4 bg-surface hover:bg-hover border border-main hover:border-primary-start/50 rounded-2xl cursor-pointer transition-all flex flex-col justify-between gap-3 group"
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-[9px] font-black uppercase tracking-widest text-primary-start bg-primary-start/10 px-2 py-0.5 rounded border border-primary-start/20">
                              {card.badge}
                            </span>
                            <ChevronRight size={14} className="text-text-muted group-hover:text-primary-start" />
                          </div>
                          <div>
                            <h4 className="text-xs font-black text-text-primary uppercase tracking-wide flex items-center gap-1.5 mb-1">
                              <CardIcon size={14} className="text-primary-start" />
                              {card.title}
                            </h4>
                            <p className="text-[11px] text-text-secondary line-clamp-2">{card.desc}</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {entityMessages.map((m) => (
                <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[88%] p-4 rounded-2xl text-xs leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-primary-start text-white font-medium'
                        : 'bg-surface border border-main text-text-primary font-medium'
                    }`}
                  >
                    {m.content ? <LawCitationText text={m.content} /> : <Loader2 className="animate-spin h-4 w-4 text-primary-start" />}
                  </div>
                </div>
              ))}
              <div ref={chatScrollRef} />
            </div>

            <div className="p-4 bg-surface border-t border-main shrink-0 space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputQuestion}
                  onChange={(e) => onInputChange(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && onSendQuestion()}
                  placeholder={`Bëj një pyetje për ${translateToAlbanian(chatEntity.label)}...`}
                  className="flex-1 h-11 px-4 bg-canvas border border-main rounded-xl text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-start"
                />
                <button
                  type="button"
                  onClick={() => onSendQuestion()}
                  disabled={!inputQuestion.trim() || isSending}
                  className="h-11 px-5 bg-primary-start text-white font-bold rounded-xl text-xs uppercase tracking-wider flex items-center justify-center shadow-md disabled:opacity-40"
                >
                  {isSending ? <Loader2 className="animate-spin h-4 w-4" /> : <Send size={16} />}
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};