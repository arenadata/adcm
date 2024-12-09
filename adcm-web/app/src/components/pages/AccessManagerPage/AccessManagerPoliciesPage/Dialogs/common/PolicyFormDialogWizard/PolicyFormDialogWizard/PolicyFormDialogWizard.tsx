import type React from 'react';
import s from './PolicyFormDialogWizard.module.scss';
import { TabButton, TabsBlock } from '@uikit';
import { Steps, steps } from '../constants';
import cn from 'classnames';

interface PolicyFormDialogWizardProps {
  isValid: boolean;
  currentStep: string;
  onChangeStep: (step: string) => void;
}

const PolicyFormDialogWizard: React.FC<PolicyFormDialogWizardProps> = ({ isValid, currentStep, onChangeStep }) => {
  const classNames = cn(s.stepsPanel__stepButton, {
    [s.stepsPanel__stepButton_valid]: isValid,
  });

  const handleChangeStep = (event: React.MouseEvent<HTMLButtonElement>) => {
    const stepKey = event.currentTarget.dataset.stepKey ?? '';
    onChangeStep(stepKey);
  };

  return (
    <div className={s.policyFormDialogWizard}>
      <TabsBlock variant="secondary" className={s.stepsPanel}>
        <TabButton
          className={classNames}
          isActive={currentStep === Steps.MainInfo}
          data-step-key={Steps.MainInfo}
          onClick={handleChangeStep}
        >
          <span>1</span>
          {steps[0].title}
        </TabButton>
        <TabButton
          className={classNames}
          disabled={!isValid}
          isActive={currentStep === Steps.Object}
          data-step-key={Steps.Object}
          onClick={handleChangeStep}
        >
          <span>2</span>
          {steps[1].title}
        </TabButton>
      </TabsBlock>
    </div>
  );
};

export default PolicyFormDialogWizard;
