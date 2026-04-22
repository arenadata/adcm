import type { Context } from 'react';
import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';
import type { SomeEntityArgs, WizardOwner } from '@store/adcm/entityWizard/types/wizardSlice.types';

interface EntityWizardDataContextOptions {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
}

export const EntityWizardDataContext = createContextHelper<EntityWizardDataContextOptions>('EntityWizardDataContext');

export const useEntityWizardDataContext = (): EntityWizardDataContextOptions =>
  useContextHelper<EntityWizardDataContextOptions>(
    EntityWizardDataContext as Context<EntityWizardDataContextOptions | undefined>,
  );
