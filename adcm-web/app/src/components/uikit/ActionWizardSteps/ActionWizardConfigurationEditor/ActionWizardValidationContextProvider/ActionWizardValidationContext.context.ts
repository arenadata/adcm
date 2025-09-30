import type { Context } from 'react';
import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';

interface ActionWizardValidationContextOptions {
  isValid: boolean;
  setIsValid: (valid: boolean) => void;
}

export const ActionWizardValidationContext = createContextHelper<ActionWizardValidationContextOptions>(
  'ActionWizardValidationContext',
);

export const useActionWizardValidationContext = (): ActionWizardValidationContextOptions =>
  useContextHelper<ActionWizardValidationContextOptions>(
    ActionWizardValidationContext as Context<ActionWizardValidationContextOptions | undefined>,
  );
