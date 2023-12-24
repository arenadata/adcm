import React from 'react';
import TabButton from '@uikit/Tabs/TabButton';
import { TabsBlock } from '@uikit';
import { TabsBlockProps } from '@uikit/Tabs/TabsBlock';
import { WizardStep } from '@uikit/WizardSteps/WizardSteps.types';
import { getStepIndex } from '@uikit/WizardSteps/WizardSteps.utils';

interface WizardStepProps extends Omit<TabsBlockProps, 'variant' | 'children'> {
  steps: WizardStep[];
  currentStep: WizardStep['key'];
  onChangeStep: (stepKey: WizardStep['key']) => void;
  className?: string;
}

const WizardSteps: React.FC<WizardStepProps> = ({ steps, currentStep, onChangeStep, className }) => {
  const handleChangeStep = (event: React.MouseEvent<HTMLButtonElement>) => {
    const stepKey = (event.currentTarget.dataset.stepKey ?? '') as WizardStep['key'];
    onChangeStep(stepKey);
  };

  return (
    <TabsBlock variant="secondary" className={className}>
      {steps.map((step, index) => (
        <TabButton
          isActive={currentStep === step.key}
          data-step-key={step.key}
          onClick={handleChangeStep}
          key={step.key}
          disabled={index > getStepIndex(currentStep, steps)}
        >
          {step.title}
        </TabButton>
      ))}
    </TabsBlock>
  );
};

export default WizardSteps;
