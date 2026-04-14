import type React from 'react';
import { useMemo, useEffect } from 'react';
import {
  AdcmWizardMethodType,
  AdcmWizardStepType,
  type AdcmActionProcessStep,
  AdcmWizardStepStates,
} from '@models/adcm/wizard';
import { useDispatch, useStore } from '@hooks';
import {
  type AdcmPostOperationPayload,
  postOperation,
  postOperationWithLastStep,
  postOperationWithStepReset,
  postOperationWithTask,
  resetSelectedStepId,
} from '@store/adcm/clusters/clustersWizardActionsSlice';
import { getProcess, getSteps, resetStep } from '@store/adcm/clusters/clustersWizardSlice';
import type { RunClusterDynamicActionPayload } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import ActionWizardSteps from '@uikit/ActionWizardSteps/ActionWizardSteps';
import { useActionWizardConfigurationEditorContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContext.context';
import { useActionWizardLastStageContext } from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContext.context';
import { getCurrentStageNotDisabledStepIds, getMaxStepId } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';
import ClusterDynamicActionWizardOperation from '@pages/ClustersPage/Dialogs/ClusterDynamicActionWizardDialog/ClusterDynamicActionWizardOperation/ClusterDynamicActionWizardOperation';

interface ClusterDynamicActionWizardStepProps {
  stageNumber: number;
  onClose: () => void;
}

interface SubmitStepHandlerOptions {
  isStepSkippable: boolean;
}

const ClusterDynamicActionWizardStep: React.FC<ClusterDynamicActionWizardStepProps> = ({
  stageNumber,
  onClose,
}: ClusterDynamicActionWizardStepProps) => {
  const dispatch = useDispatch();

  const clusterId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.clusterId);
  const actionId = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.processId);
  const process = useStore((s) => s.adcm.clustersWizard.process);
  const inProgress = useStore(({ adcm }) => adcm.clustersWizardActions.wizardDialog.inProgress);
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);
  const stepsWithData = useStore(({ adcm }) => adcm.clustersWizard.steps);
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);
  const hostComponentMapDelta = useStore(({ adcm }) => adcm.clustersWizardMapping.hostComponentMapDelta);
  const actionDetails = useStore(({ adcm }) => adcm.clustersDynamicActions.dialog.actionDetails);
  const step = useStore(({ adcm }) => adcm.clustersWizard.step);

  const { configuration } = useActionWizardConfigurationEditorContext();
  const { formData } = useActionWizardLastStageContext();

  const currentStep = selectedStep ?? process?.currentStep;

  const isInRunningState = useMemo(() => {
    return process?.stages.some((stage) => stage.steps.some((step) => step.state === 'running')) || false;
  }, [process?.stages]);

  const stageMaxIds = useMemo(() => {
    return (
      process?.stages.reduce(
        (acc, stage, index) => {
          acc[index] = getMaxStepId(stage.steps);
          return acc;
        },
        {} as Record<number, AdcmActionProcessStep['id']>,
      ) ?? {}
    );
  }, [process?.stages]);

  const stepIds = useMemo(() => {
    return process && processId === process.id && process.stages.length > 0 && currentStep
      ? getCurrentStageNotDisabledStepIds(currentStep, process?.currentStep, process.stages)
      : [];
  }, [currentStep, processId, process?.stages]);

  const isMaxStepInStage = useMemo(() => currentStep === stageMaxIds[stageNumber - 1], [currentStep, stageNumber]);

  const steps = useMemo(() => {
    if (
      stepsWithData.length === 0 ||
      // (process?.stages.at(-2) - `-2` is real last stage (manual last stage we append after get/update process)
      // only in case when currentStepId > maxStepId from real last stage -> we show imaginary last stage (which we manually appended)
      (currentStep && currentStep > getMaxStepId(process?.stages.at(-2)?.steps ?? []))
    ) {
      return process?.stages.at(-1)?.steps;
    } else {
      return stepsWithData;
    }
  }, [stepsWithData, currentStep, process?.stages]);

  const stepToStageMap = useMemo(() => {
    return new Map<number, string>(
      process?.stages.flatMap((stage) => stage.steps.map((step) => [step.id, stage.displayName])),
    );
  }, [process?.stages]);

  const isCurrentStepBroken = useMemo(() => {
    if (!process) return false;

    const allSteps = process.stages.flatMap((stage) => stage.steps);
    const step = allSteps.find((step) => step.id === process.currentStep);

    return step?.state === AdcmWizardStepStates.Broken;
  }, [process]);

  const isCurrentStepRunning = useMemo(() => {
    if (!steps) return false;

    const step = steps.find((step) => step.id === process?.currentStep);

    return step?.state === AdcmWizardStepStates.Running;
  }, [selectedStep]);

  const neededStageName = useMemo(() => {
    if (currentStep) {
      return stepToStageMap.get(currentStep);
    }
  }, [currentStep, stepToStageMap]);

  const loadedStageName = useMemo(() => {
    if (stepsWithData.length > 0) {
      const firstStepId = stepsWithData[0].id;
      return stepToStageMap.get(firstStepId);
    }
  }, [stepsWithData, stepToStageMap]);

  // we need to check if selectedStep(clicked) is in the different stage with current step
  // lint doesn't react to deps
  const isNeedToLoadSteps = useMemo(() => {
    if (selectedStep && !isCurrentStepRunning) {
      return neededStageName !== loadedStageName;
    }

    return true;
  }, [selectedStep, steps]);

  useEffect(() => {
    if ((isCurrentStepBroken || isNeedToLoadSteps) && processId && clusterId && actionId && stepIds.length > 0) {
      dispatch(
        getSteps({
          clusterId,
          actionId,
          processId,
          stepIds,
        }),
      );
    }
  }, [dispatch, stepIds, selectedStep]);

  const handleSubmitStep = (stepType: string, options?: SubmitStepHandlerOptions) => {
    if (!clusterId || !actionId || !process) {
      return;
    }

    if (stepType === AdcmWizardStepType.Configuration) {
      const data = configuration[process.currentStep];
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

      if (options?.isStepSkippable) {
        payload.operation.method = AdcmWizardMethodType.SkipStep;
      }

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

    if (stepType === AdcmWizardStepType.Mapping) {
      const postMappingPayload: AdcmPostOperationPayload = {
        clusterId,
        actionId,
        processId: process.id,
        operation: {
          method: AdcmWizardMethodType.Submit,
          params: {
            stepId: process.currentStep,
            processSyncKey: process.syncKey,
            hostComponentMapDelta: hostComponentMapDelta,
          },
        },
      };

      dispatch(postOperation(postMappingPayload));
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
          isVerbose: formData.isVerbose,
          shouldBlockObject: formData.shouldBlockObject,
          description: formData.description,
          process: {
            id: process.id,
          },
        },
      };

      dispatch(postOperationWithLastStep({ postOperationPayload, lastStepPayload }));
    }
  };

  const handleResetStep = (stepId: number) => {
    if (!clusterId || !actionId || !process || inProgress) {
      return;
    }

    const postOperationPayload: AdcmPostOperationPayload = {
      clusterId,
      actionId,
      processId: process.id,
      operation: {
        method: AdcmWizardMethodType.Reset,
        params: {
          stepId,
          processSyncKey: process.syncKey,
        },
      },
    };

    dispatch(postOperationWithStepReset({ postOperationPayload, stepId }));
  };

  const handleChangeStep = () => {
    if (clusterId && actionId && process && currentStep && step) {
      if (isMaxStepInStage) {
        dispatch(resetStep());
      }

      if (!step.required && step.type === AdcmWizardStepType.Operation && step.state === AdcmWizardStepStates.Created) {
        handleSubmitStep(step.type, { isStepSkippable: true });
      }

      dispatch(resetSelectedStepId());
      dispatch(getProcess({ clusterId, actionId, processId: process.id }));
    }
  };

  if (!steps || !process || !clusterId || processId !== process.id) return null;

  return (
    <ActionWizardSteps
      clusterId={clusterId}
      jobsData={jobsData}
      selectedStep={selectedStep}
      currentStep={process.currentStep}
      stageNumber={stageNumber}
      steps={steps}
      isInRunningState={isInRunningState}
      onStepSubmit={handleSubmitStep}
      onStepChange={handleChangeStep}
      onStepReset={handleResetStep}
      onClose={onClose}
      entityDynamicActionWizardOperation={ClusterDynamicActionWizardOperation}
      lastStepActionDetails={actionDetails}
    />
  );
};

export default ClusterDynamicActionWizardStep;
