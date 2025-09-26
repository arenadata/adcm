import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import Panel from '@uikit/Panel/Panel';
import s from './ActionWizardSteps.module.scss';
import { type AdcmActionProcessStep, AdcmWizardStepType } from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import ClusterDynamicActionWizardOperation from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/ClusterDynamicActionWizardOperation/ClusterDynamicActionWizardOperation';
import ActionWizardConfigurationEditor from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditor';
import ActionWizardLastStage from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStage';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';

interface ActionWizardStepProps {
  stageNumber: number;
  steps: AdcmActionProcessStep[];
  onStepSubmit: (stepType: AdcmWizardStepType) => void;
  onStepChange: () => void;
  onStepReset: () => void;
}

const getStepIcon = (step: AdcmActionProcessStep, isValid: boolean) => {
  if (!isValid || step.state === 'broken') {
    return <MarkerIcon variant="round" type="alert" size={12} />;
  }
  if (step.state === 'completed') {
    return <MarkerIcon variant="round" type="check" size={12} />;
  }

  return undefined;
};

const stepPanelLabelClassName = (step: AdcmActionProcessStep, isValid: boolean) => {
  return cn(s.actionWizardSteps__stageInfo, {
    [s.actionWizardSteps__stageInfo_running]: step.state === 'running',
    [s.actionWizardSteps__stageInfo_error]: !isValid || step.state === 'broken',
    [s.actionWizardSteps__stageInfo_completed]: step.state === 'completed',
  });
};

const isButtonDisabled = (step: AdcmActionProcessStep) => {
  if (step.type === AdcmWizardStepType.Operation) {
    return step.state !== 'completed';
  }

  return step.state === 'completed';
};

const isFirstButtonVisible = (stepType: AdcmWizardStepType) => {
  return [AdcmWizardStepType.Operation, AdcmWizardStepType.Configuration].includes(stepType);
};

const ActionWizardSteps = ({ stageNumber, steps, onStepSubmit, onStepChange, onStepReset }: ActionWizardStepProps) => {
  const { isValid } = useActionWizardValidationContext();

  const handleFirstButtonClick = (stepType: AdcmWizardStepType) => {
    if (stepType === AdcmWizardStepType.Operation) {
      onStepSubmit(stepType);
    } else {
      onStepReset();
    }
  };

  const handleSecondButtonClick = (stepType: AdcmWizardStepType) => {
    if (stepType === AdcmWizardStepType.Operation) {
      onStepChange();
    } else {
      onStepSubmit(stepType);
    }
  };

  return (
    <div className={s.actionWizardSteps__steps}>
      {steps.map((step, stepIndex) => (
        <div key={step.id} className={s.actionWizardSteps__step}>
          <Panel className={s.actionWizardSteps__panel}>
            <div className={stepPanelLabelClassName(step, isValid)}>
              <div className={s.actionWizardSteps__stageNumber}>
                {stageNumber}.{stepIndex + 1}
                {getStepIcon(step, isValid)}
              </div>
              <div className={s.actionWizardSteps__stepLabel}>{step.displayName}</div>
            </div>
            <ButtonGroup className={s.actionWizardSteps__buttons}>
              {isFirstButtonVisible(step.type) && (
                <Button variant="secondary" onClick={() => handleFirstButtonClick(step.type)}>
                  {step.type === AdcmWizardStepType.Operation ? step.uiOptions.buttonName : 'Discard changes'}
                </Button>
              )}
              <Button
                onClick={() => handleSecondButtonClick(step.type)}
                hasError={!isValid}
                disabled={!isValid || isButtonDisabled(step)}
              >
                {step.type === AdcmWizardStepType.LastStep ? 'Run' : 'Next step'}
              </Button>
            </ButtonGroup>
          </Panel>
          <div className={s.actionWizardSteps__content}>
            {step.type === AdcmWizardStepType.Configuration && <ActionWizardConfigurationEditor step={step} />}
            {step.type === AdcmWizardStepType.Operation && <ClusterDynamicActionWizardOperation step={step} />}
            {step.type === AdcmWizardStepType.LastStep && <ActionWizardLastStage />}
          </div>
        </div>
      ))}
    </div>
  );
};

export default ActionWizardSteps;
