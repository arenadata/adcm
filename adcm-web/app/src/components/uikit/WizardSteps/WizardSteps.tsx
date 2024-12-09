import type React from 'react';
import TabButton from '@uikit/Tabs/TabButton';
import { TabsBlock } from '@uikit';
import type { TabsBlockProps } from '@uikit/Tabs/TabsBlock';
import type { WizardStep } from '@uikit/WizardSteps/WizardSteps.types';
import { getStepIndex } from '@uikit/WizardSteps/WizardSteps.utils';
import s from './WizardSteps.module.scss';
import cn from 'classnames';

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
    <TabsBlock variant="secondary" className={cn(className, s.wizardSteps)}>
      {steps.map((step, index) => (
        <TabButton
          className={s.tabButton}
          isActive={currentStep === step.key}
          data-step-key={step.key}
          onClick={handleChangeStep}
          key={step.key}
          disabled={index > getStepIndex(currentStep, steps)}
        >
          <span className={s.tabButton__stepNumber}>{index + 1}</span>
          {step.title}
        </TabButton>
      ))}
    </TabsBlock>
  );
};

export default WizardSteps;
