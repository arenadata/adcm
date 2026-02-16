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
} from '@models/adcm/wizard';
import MarkerIcon from '@uikit/MarkerIcon/MarkerIcon';
import cn from 'classnames';
import ActionWizardConfigurationEditorContextProvider from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContextProvider';
import { useActionWizardValidationContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardValidationContextProvider/ActionWizardValidationContext.context';
import { type AdcmJob, AdcmJobStatus } from '@models/adcm';
import ActionWizardLastStageContextProvider from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContextProvider';
import ActionWizardBrokenStage from '@uikit/ActionWizardSteps/ActionWizardBrokenStage/ActionWizardBrokenStage';
import FlexGroup from '@uikit/FlexGroup/FlexGroup';
import { getStepTip } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';

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

interface ActionWizardProps {
  stages: AdcmWizardStage[];
  currentStep: number;
  process: AdcmActionWizardProcess;
  jobsData: AdcmWizardJobsData;
  onClose: () => void;
  selectedStep?: number;
  brokenStepError?: string;
  wizardTitle: string;
  onSetBrokenStepError: (error?: string) => void;
  onSetSelectedStepId: (id: number) => void;
  entityDynamicActionWizardStepComponent: React.FC<{
    stageNumber: number;
    onClose: () => void;
  }>;
}

const ActionWizard: React.FC<ActionWizardProps> = ({
  wizardTitle,
  stages,
  selectedStep,
  brokenStepError,
  currentStep,
  process,
  jobsData,
  onClose,
  onSetBrokenStepError,
  onSetSelectedStepId,
  entityDynamicActionWizardStepComponent,
}) => {
  const stepId = selectedStep ?? currentStep;
  const ActionWizardStepComponent = entityDynamicActionWizardStepComponent;

  const { isValid } = useActionWizardValidationContext();

  const stageIndex = useMemo(() => {
    return stages.findIndex((stage) => stage.steps.some((step) => step.id === stepId));
  }, [stages, selectedStep]);

  if (!stages || stageIndex < 0 || !ActionWizardStepComponent) return null;

  return (
    <div className={s.actionWizardLayout}>
      <aside className={s.actionWizardLayout__leftSidebarWrap} data-test="nav-menu">
        <ActionWizardMap
          wizardTitle={wizardTitle}
          process={process}
          jobsData={jobsData}
          selectedStep={stepId}
          onSetBrokenStepError={onSetBrokenStepError}
          onSetSelectedStepId={onSetSelectedStepId}
        />
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
                <ActionWizardStepComponent stageNumber={stageIndex + 1} onClose={onClose} />
              </ActionWizardLastStageContextProvider>
            </ActionWizardConfigurationEditorContextProvider>
          </>
        )}
      </div>
    </div>
  );
};

export default ActionWizard;
