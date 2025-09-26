import type React from 'react';
import { useMemo } from 'react';
import ActionWizardMap from '@uikit/ActionWizardMap/ActionWizardMap';
import s from './ActionWizard.module.scss';
import Button from '@uikit/Button/Button';
import Icon from '@uikit/Icon/Icon';
import type { AdcmActionWizardProcess, AdcmWizardStage } from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import ClusterDynamicActionWizardStep from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/ClusterDynamicActionWizardStep/ClusterDynamicActionWizardStep';
import ActionWizardConfigurationEditorContextProvider from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContextProvider';
import { useStore } from '@hooks';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';

const getTitleIcon = (stage: AdcmWizardStage, isValid: boolean) => {
  if (stage.steps.some((step) => step.state === 'running')) {
    return <Icon className={s.actionWizardLayout__runningIcon} name="g1-hourglass" />;
  }
  if (stage.steps.every((step) => step.state === 'completed') && isValid) {
    return <MarkerIcon variant="round" type="check" size={20} />;
  }

  return undefined;
};

const stageLabelClassName = (stage: AdcmWizardStage, isValid: boolean) => {
  return cn(s.actionWizardLayout__label, {
    [s.actionWizardLayout__label_running]: stage.steps.some((step) => step.state === 'running'),
    [s.actionWizardLayout__label_error]: !isValid || stage.steps.some((step) => step.state === 'broken'),
    [s.actionWizardLayout__label_completed]: stage.steps.every((step) => step.state === 'completed'),
  });
};

const getStepTip = (stage: AdcmWizardStage) => {
  if (stage.steps.some((step) => step.state === 'created')) {
    return 'Fill inputs';
  }
  if (stage.steps.every((step) => step.state === 'completed')) {
    return 'Proceed to next step';
  }
  if (stage.steps.some((step) => step.state === 'running')) {
    return 'Running';
  }
};

interface ActionWizardProps {
  stages: AdcmWizardStage[];
  currentStep: number;
  process: AdcmActionWizardProcess;
  onClose?: () => void;
}

const ActionWizard: React.FC<ActionWizardProps> = ({ stages, currentStep, process, onClose }) => {
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);

  const { isValid } = useActionWizardValidationContext();

  const stageIndex = useMemo(() => {
    const stepId = selectedStep ?? currentStep;
    return stages.findIndex((stage) => stage.steps.some((step) => step.id === stepId));
  }, [stages, selectedStep]);

  if (!stages || stageIndex < 0) return null;

  return (
    <div className={s.actionWizardLayout}>
      <aside className={s.actionWizardLayout__leftSidebarWrap} data-test="nav-menu">
        <ActionWizardMap process={process} />
      </aside>
      <div className={s.actionWizardLayout__content}>
        <header className={s.actionWizardLayout__header}>
          <div className={s.actionWizardLayout__title}>
            <div style={{ display: 'flex', gap: '16px' }}>
              <span className={stageLabelClassName(stages[stageIndex], isValid)}>{stages[stageIndex].displayName}</span>
              {getTitleIcon(stages[stageIndex], isValid)}
            </div>
            <span className={s.actionWizardLayout__tip}>{getStepTip(stages[stageIndex])}</span>
          </div>
          <Button className={s.actionWizardLayout__exitButton} variant="secondary" onClick={onClose}>
            Exit
          </Button>
        </header>
        <ActionWizardConfigurationEditorContextProvider>
          <ClusterDynamicActionWizardStep stageNumber={stageIndex + 1} />
        </ActionWizardConfigurationEditorContextProvider>
      </div>
    </div>
  );
};

export default ActionWizard;
