import type React from 'react';
import { useMemo } from 'react';
import ActionWizardMap from '@uikit/ActionWizardMap/ActionWizardMap';
import s from './ActionWizard.module.scss';
import Button from '@uikit/Button/Button';
import Icon from '@uikit/Icon/Icon';
import {
  type AdcmActionWizardProcess,
  type AdcmWizardJobsData,
  type AdcmWizardStage,
  AdcmWizardStepStates,
  AdcmWizardStepType,
} from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import ClusterDynamicActionWizardStep from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/ClusterDynamicActionWizardStep/ClusterDynamicActionWizardStep';
import ActionWizardConfigurationEditorContextProvider from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContextProvider';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';
import { type AdcmJob, AdcmJobStatus } from '@models/adcm';
import ActionWizardLastStageContextProvider from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContextProvider';
import ActionWizardBrokenStage from '@uikit/ActionWizardSteps/ActionWizardBrokenStage/ActionWizardBrokenStage';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';

const tips = {
  [AdcmWizardStepStates.Created]: 'Fill inputs',
  [AdcmWizardStepStates.Completed]: 'Proceed to next step',
  [AdcmWizardStepStates.Running]: 'Running',
  [AdcmWizardStepStates.Broken]: 'Broken',
};

const getTitleIcon = (stage: AdcmWizardStage, isValid: boolean) => {
  if (stage.steps.some((step) => step.state === AdcmWizardStepStates.Running)) {
    return <Icon className={s.actionWizardLayout__runningIcon} name="g1-hourglass" />;
  }
  if (stage.steps.every((step) => step.state === AdcmWizardStepStates.Completed) && isValid) {
    return <MarkerIcon variant="round" type="check" size={20} />;
  }

  return undefined;
};

const stageLabelClassName = (stage: AdcmWizardStage, isValid: boolean, jobsData?: AdcmJob) => {
  return cn(s.actionWizardLayout__label, {
    [s.actionWizardLayout__label_running]: stage.steps.some((step) => step.state === AdcmWizardStepStates.Running),
    [s.actionWizardLayout__label_error]:
      !isValid ||
      jobsData?.status === AdcmJobStatus.Failed ||
      stage.steps.some((step) => step.state === AdcmWizardStepStates.Broken),
    [s.actionWizardLayout__label_completed]: stage.steps.every((step) => step.state === AdcmWizardStepStates.Completed),
  });
};

const getStepTip = (stage: AdcmWizardStage, currentStep: number) => {
  const step = stage.steps.find((step) => step.id === currentStep);

  if (step) {
    if (step.type === AdcmWizardStepType.Operation || step.type === AdcmWizardStepType.LastStep) {
      return tips[AdcmWizardStepStates.Completed];
    }

    return tips[step.state as AdcmWizardStepStates];
  }
};

interface ActionWizardProps {
  stages: AdcmWizardStage[];
  currentStep: number;
  process: AdcmActionWizardProcess;
  jobsData: AdcmWizardJobsData;
  onClose: () => void;
  selectedStep?: number;
  brokenStepError?: string;
}

const ActionWizard: React.FC<ActionWizardProps> = ({
  stages,
  selectedStep,
  brokenStepError,
  currentStep,
  process,
  jobsData,
  onClose,
}) => {
  const stepId = selectedStep ?? currentStep;

  const { isValid } = useActionWizardValidationContext();

  const stageIndex = useMemo(() => {
    return stages.findIndex((stage) => stage.steps.some((step) => step.id === stepId));
  }, [stages, selectedStep]);

  if (!stages || stageIndex < 0) return null;

  return (
    <div className={s.actionWizardLayout}>
      <aside className={s.actionWizardLayout__leftSidebarWrap} data-test="nav-menu">
        <ActionWizardMap process={process} />
      </aside>
      <div className={s.actionWizardLayout__content}>
        {brokenStepError && <ActionWizardBrokenStage brokenStepError={brokenStepError} onClose={onClose} />}
        {!brokenStepError && (
          <>
            <header className={s.actionWizardLayout__header}>
              <div className={s.actionWizardLayout__title}>
                <FlexGroup gap="16px">
                  <span className={stageLabelClassName(stages[stageIndex], isValid, jobsData[stepId]?.job)}>
                    {stages[stageIndex].displayName}
                  </span>
                  {getTitleIcon(stages[stageIndex], isValid)}
                </FlexGroup>
                <span className={s.actionWizardLayout__tip}>
                  {getStepTip(stages[stageIndex], selectedStep ?? currentStep)}
                </span>
              </div>
              <Button className={s.actionWizardLayout__exitButton} variant="secondary" onClick={onClose}>
                Exit
              </Button>
            </header>
            <ActionWizardConfigurationEditorContextProvider>
              <ActionWizardLastStageContextProvider>
                <ClusterDynamicActionWizardStep stageNumber={stageIndex + 1} />
              </ActionWizardLastStageContextProvider>
            </ActionWizardConfigurationEditorContextProvider>
          </>
        )}
      </div>
    </div>
  );
};

export default ActionWizard;
