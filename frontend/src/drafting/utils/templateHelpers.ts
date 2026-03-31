// FILE: src/drafting/utils/templateHelpers.ts
// ARCHITECTURE: TEMPLATE ORCHESTRATION LAYER

import { TemplateType } from '../types';
import { templateConfigs } from '../templates';

/**
 * Safely retrieves structure instructions.
 * If the template is missing, it logs a warning in development and falls back to generic.
 */
export const getDocumentStructureInstructions = (template: TemplateType): string => {
  const config = templateConfigs[template];
  
  if (!config) {
    console.warn(`[DraftingEngine] Template '${template}' not found. Falling back to generic.`);
    return templateConfigs.generic.structureInstructions;
  }

  // Ensure instructions are clean and well-spaced for the LLM prompt injection
  return config.structureInstructions.trim();
};

/**
 * Safely retrieves placeholder text for the UI.
 * Provides the user with a specific hint on how to structure their input.
 */
export const getTemplatePlaceholder = (template: TemplateType): string => {
  const config = templateConfigs[template];
  
  if (!config) {
    return templateConfigs.generic.placeholder;
  }

  return config.placeholder;
};

/**
 * Optional: Helper to get the display label for the UI (future-proofing)
 */
export const getTemplateLabel = (template: TemplateType): string => {
  return templateConfigs[template]?.label || 'Dokument i Përgjithshëm';
};