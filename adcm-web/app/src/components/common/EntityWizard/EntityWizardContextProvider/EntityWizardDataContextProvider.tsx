import type React from 'react';
import { EntityWizardDataContext } from './EntityWizardData.context';
import type { WizardOwner, SomeEntityArgs } from '@store/adcm/entityWizard/types/wizardSlice.types';

interface EntityWizardDataContextProvider {
  entityType: WizardOwner;
  entityArgs: SomeEntityArgs;
  children: React.ReactNode;
}

export const EntityWizardDataContextProvider: React.FC<EntityWizardDataContextProvider> = ({
  children,
  entityType,
  entityArgs,
}) => {
  return (
    <EntityWizardDataContext.Provider value={{ entityType, entityArgs }}>{children}</EntityWizardDataContext.Provider>
  );
};
