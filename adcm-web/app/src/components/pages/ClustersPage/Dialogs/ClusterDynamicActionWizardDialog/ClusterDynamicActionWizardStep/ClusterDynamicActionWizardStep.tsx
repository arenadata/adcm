import type React from 'react';
import { useMemo } from 'react';
import { useEffect } from 'react';
import { AdcmWizardMethodType, type AdcmWizardStage, AdcmWizardStepType } from '@models/adcm/wizard';
import { useDispatch, useStore } from '@hooks';
import {
  type AdcmPostOperationPayload,
  postOperation,
  postOperationWithLastStep,
  postOperationWithTask,
  resetSelectedStepId,
} from '@store/adcm/clusters/clustersWizardActionsSlice';
import { getProcess, getSteps, resetJobData, resetStep } from '@store/adcm/clusters/clustersWizardSlice';
import type { RunClusterDynamicActionPayload } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import ActionWizardSteps from '@uikit/ActionWizardSteps/ActionWizardSteps';
import { useActionWizardConfigurationEditorContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContext.context';

interface ClusterDynamicActionWizardStepProps {
  stageNumber: number;
}

const getCurrentStageNotDisabledStepIds = (currentStep: number, stages: AdcmWizardStage[]): number[] => {
  const currentStage = stages.find((stage) =>
    stage.steps.some((step) => step.id === currentStep && step.type !== AdcmWizardStepType.LastStep),
  );

  if (!currentStage) {
    return [];
  }

  return currentStage.steps.filter((step) => step.id <= currentStep).map((step) => step.id);
};

const ClusterDynamicActionWizardStep: React.FC<ClusterDynamicActionWizardStepProps> = ({
  stageNumber,
}: ClusterDynamicActionWizardStepProps) => {
  const dispatch = useDispatch();

  const clusterId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.clusterId);
  const actionId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.actionId);
  const process = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.process);
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);
  const stepsWithData = useStore(({ adcm }) => adcm.clustersWizard.steps);

  const { configuration } = useActionWizardConfigurationEditorContext();

  const currentStep = selectedStep ?? process?.currentStep;

  const stepIds = useMemo(() => {
    return process && process.stages.length > 0 && currentStep
      ? getCurrentStageNotDisabledStepIds(currentStep, process.stages)
      : [];
  }, [currentStep, process?.stages]);

  const maxStepId = useMemo(
    () => (stepsWithData.length > 0 ? Math.max(...stepsWithData.map((step) => step.id)) : -1),
    [stepsWithData],
  );

  const steps = useMemo(() => {
    if (stepsWithData.length === 0 || (currentStep && currentStep > maxStepId)) {
      return process?.stages.at(-1)?.steps;
    } else {
      return stepsWithData;
    }
  }, [stepsWithData, currentStep, process?.stages, maxStepId]);

  useEffect(() => {
    if (process && clusterId && actionId) {
      dispatch(
        getSteps({
          clusterId,
          actionId,
          processId: process.id,
          stepIds,
        }),
      );
    }
  }, [dispatch, stepIds, selectedStep]);

  const handleSubmitStep = (stepType: string) => {
    if (!clusterId || !actionId || !process) {
      return;
    }

    if (stepType === AdcmWizardStepType.Configuration) {
      const data = configuration;
      if (!data) return;

      const payload: AdcmPostOperationPayload = {
        clusterId,
        actionId,
        processId: process.id,
        operation: {
          method: AdcmWizardMethodType.Submit,
          params: {
            stepId: process.currentStep,
            processSyncKey: process.syncKey,
            configuration: {
              adcmMeta: data.attributes,
              config: data.configurationData,
            },
          },
        },
      };

      dispatch(postOperation(payload));
    }

    if (stepType === AdcmWizardStepType.Operation) {
      const payload: AdcmPostOperationPayload = {
        clusterId,
        actionId,
        processId: process.id,
        operation: {
          method: AdcmWizardMethodType.Submit,
          params: {
            stepId: process.currentStep,
            processSyncKey: process.syncKey,
          },
        },
      };

      dispatch(
        postOperationWithTask({
          clusterId,
          actionId,
          processId: process.id,
          stepId: process.currentStep,
          postOperationPayload: payload,
        }),
      );
    }

    if (stepType === AdcmWizardStepType.LastStep) {
      const postOperationPayload: AdcmPostOperationPayload = {
        clusterId,
        actionId,
        processId: process.id,
        operation: {
          method: AdcmWizardMethodType.Complete,
          params: {
            processSyncKey: process.syncKey,
          },
        },
      };

      const lastStepPayload: RunClusterDynamicActionPayload = {
        clusterId,
        actionId,
        actionRunConfig: {
          configuration: null,
          hostComponentMap: [],
          isVerbose: false,
          shouldBlockObject: true,
          process: {
            id: process.id,
          },
        },
      };

      dispatch(postOperationWithLastStep({ postOperationPayload, lastStepPayload }));
    }
  };

  const handleResetStep = () => {
    if (!clusterId || !actionId || !process || !currentStep) {
      return;
    }

    const payload: AdcmPostOperationPayload = {
      clusterId,
      actionId,
      processId: process.id,
      operation: {
        method: AdcmWizardMethodType.Reset,
        params: {
          stepId: currentStep,
          processSyncKey: process.syncKey,
        },
      },
    };

    dispatch(postOperation(payload));
  };

  const handleChangeStep = () => {
    if (clusterId && actionId && process) {
      dispatch(resetSelectedStepId());
      dispatch(resetStep());
      dispatch(resetJobData());
      dispatch(getProcess({ clusterId, actionId, processId: process.id }));
    }
  };

  if (!steps || !process) return null;

  return (
    <ActionWizardSteps
      stageNumber={stageNumber}
      steps={steps}
      onStepSubmit={handleSubmitStep}
      onStepChange={handleChangeStep}
      onStepReset={handleResetStep}
    />
  );
};

export default ClusterDynamicActionWizardStep;
