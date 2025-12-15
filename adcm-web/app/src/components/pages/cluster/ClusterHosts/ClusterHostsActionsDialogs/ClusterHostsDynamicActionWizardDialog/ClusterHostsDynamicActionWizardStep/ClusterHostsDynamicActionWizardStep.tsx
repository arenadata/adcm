import type React from 'react';
import { useMemo, useEffect } from 'react';
import {
  AdcmWizardMethodType,
  AdcmWizardStepType,
  type AdcmActionProcessStep,
  AdcmWizardStepStates,
} from '@models/adcm/wizard';
import { useDispatch, useStore } from '@hooks';
import ActionWizardSteps from '@uikit/ActionWizardSteps/ActionWizardSteps';
import { useActionWizardConfigurationEditorContext } from '@uikit/ActionWizardSteps/ActionWizardConfigurationEditor/ActionWizardConfigurationEditorContextProvider/ActionWizardConfigurationEditorContext.context';
import { useActionWizardLastStageContext } from '@uikit/ActionWizardSteps/ActionWizardLastStage/ActionWizardLastStageContextProvider/ActionWizardLastStageContext.context';
import { getCurrentStageNotDisabledStepIds, getMaxStepId } from '@uikit/ActionWizardSteps/ActionWizardSteps.utils';
import { getProcess, getSteps, resetStep } from '@store/adcm/cluster/hosts/hostsWizardSlice';
import {
  type AdcmPostOperationPayload,
  postOperation,
  postOperationWithLastStep,
  postOperationWithStepReset,
  postOperationWithTask,
  resetSelectedStepId,
} from '@store/adcm/cluster/hosts/hostsWizardActionsSlice';
import type { RunClusterHostDynamicActionPayload } from '@store/adcm/cluster/hosts/hostsDynamicActionsSlice';
import ClusterHostsDynamicActionWizardOperation from '@pages/cluster/ClusterHosts/ClusterHostsActionsDialogs/ClusterHostsDynamicActionWizardDialog/ClusterHostsDynamicActionWizardOperation/ClusterHostsDynamicActionWizardOperation';

interface ClusterHostsDynamicActionWizardStepProps {
  stageNumber: number;
  onClose: () => void;
}

const ClusterHostsDynamicActionWizardStep: React.FC<ClusterHostsDynamicActionWizardStepProps> = ({
  stageNumber,
  onClose,
}: ClusterHostsDynamicActionWizardStepProps) => {
  const dispatch = useDispatch();

  const clusterId = useStore(({ adcm }) => adcm.clusterHostsWizardActions.wizardDialog.clusterId);
  const hostId = useStore(({ adcm }) => adcm.clusterHostsWizardActions.wizardDialog.hostId);
  const actionId = useStore(({ adcm }) => adcm.clusterHostsWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clusterHostsWizardActions.wizardDialog.processId);
  const process = useStore((s) => s.adcm.clusterHostsWizard.process);
  const inProgress = useStore(({ adcm }) => adcm.clusterHostsWizardActions.wizardDialog.inProgress);
  const selectedStep = useStore((s) => s.adcm.clusterHostsWizardActions.selectedStepId);
  const stepsWithData = useStore(({ adcm }) => adcm.clusterHostsWizard.steps);
  const jobsData = useStore((s) => s.adcm.clusterHostsWizard.jobsData);
  const hostComponentMapDelta = useStore(({ adcm }) => adcm.clustersWizardMapping.hostComponentMapDelta);

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
    if (stepsWithData.length === 0 || (currentStep && currentStep > getMaxStepId(stepsWithData))) {
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
    if (
      (isCurrentStepBroken || isNeedToLoadSteps) &&
      processId &&
      clusterId &&
      hostId &&
      actionId &&
      stepIds.length > 0
    ) {
      dispatch(
        getSteps({
          clusterId,
          hostId,
          actionId,
          processId,
          stepIds,
        }),
      );
    }
  }, [dispatch, stepIds, selectedStep]);

  const handleSubmitStep = (stepType: string) => {
    if (!clusterId || !hostId || !actionId || !process) {
      return;
    }

    if (stepType === AdcmWizardStepType.Configuration) {
      const data = configuration[process.currentStep];
      if (!data) return;

      const payload: AdcmPostOperationPayload = {
        clusterId,
        hostId,
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
        hostId,
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
          hostId,
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
        hostId,
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
        hostId,
        actionId,
        processId: process.id,
        operation: {
          method: AdcmWizardMethodType.Complete,
          params: {
            processSyncKey: process.syncKey,
          },
        },
      };

      const lastStepPayload: RunClusterHostDynamicActionPayload = {
        clusterId,
        hostId,
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
    if (!clusterId || !hostId || !actionId || !process || inProgress) {
      return;
    }

    const postOperationPayload: AdcmPostOperationPayload = {
      clusterId,
      hostId,
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
    if (clusterId && hostId && actionId && process && currentStep) {
      if (isMaxStepInStage) {
        dispatch(resetStep());
      }
      dispatch(resetSelectedStepId());
      dispatch(getProcess({ clusterId, hostId, actionId, processId: process.id }));
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
      entityDynamicActionWizardOperation={ClusterHostsDynamicActionWizardOperation}
    />
  );
};

export default ClusterHostsDynamicActionWizardStep;
