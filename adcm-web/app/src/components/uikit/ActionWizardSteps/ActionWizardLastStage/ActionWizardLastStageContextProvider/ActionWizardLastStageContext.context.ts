import type { Context } from 'react';
import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';

export interface AdcmWizardLastStageContextProps {
  isVerbose: boolean;
  shouldBlockObject: boolean;
  description: string;
}

export interface ActionWizardLastStageContextOptions {
  formData: AdcmWizardLastStageContextProps;
  onChange: (changes: Partial<AdcmWizardLastStageContextProps>) => void;
}

export const ActionWizardLastStageContext =
  createContextHelper<ActionWizardLastStageContextOptions>('ActionWizardLastStageContext');

export const useActionWizardLastStageContext = (): ActionWizardLastStageContextOptions =>
  useContextHelper<ActionWizardLastStageContextOptions>(
    ActionWizardLastStageContext as Context<ActionWizardLastStageContextOptions | undefined>,
  );
