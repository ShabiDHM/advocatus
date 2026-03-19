// src/drafting/utils/templateHelpers.ts
import { TemplateType } from '../types';
import { templateConfigs } from '../templates';

/**
 * Returns the structure instructions for the given template.
 * Falls back to generic template if the specific template is not found.
 */
export const getDocumentStructureInstructions = (template: TemplateType): string => {
  return templateConfigs[template]?.structureInstructions || templateConfigs.generic.structureInstructions;
};

/**
 * Returns the example placeholder text for the given template.
 * Falls back to generic placeholder if the specific template is not found.
 */
export const getTemplatePlaceholder = (template: TemplateType): string => {
  return templateConfigs[template]?.placeholder || templateConfigs.generic.placeholder;
};