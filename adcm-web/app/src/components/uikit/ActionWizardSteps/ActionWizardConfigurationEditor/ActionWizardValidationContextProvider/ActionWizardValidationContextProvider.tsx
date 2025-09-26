import type React from 'react';
import { useState } from 'react';
import { ActionWizardValidationContext } from './ActionWizardValidationContext.context';

interface ActionWizardValidationContextProvider {
  children: React.ReactNode;
}

export const ActionWizardValidationContextProvider: React.FC<ActionWizardValidationContextProvider> = ({
  children,
}) => {
  const [isValid, setIsValid] = useState(true);
  return (
    <ActionWizardValidationContext.Provider value={{ isValid, setIsValid }}>
      {children}
    </ActionWizardValidationContext.Provider>
  );
};
