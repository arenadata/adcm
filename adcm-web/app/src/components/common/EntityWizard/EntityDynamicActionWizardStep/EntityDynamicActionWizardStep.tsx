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
import EntityDynamicActionWizardOperation from '../EntityDynamicActionWizardOperation/EntityDynamicActionWizardOperation';
import { getProcess, getSteps, resetStep } from '@store/adcm/entityWizard/wizardSlice';
import type { AdcmPostOperationPayload } from '@store/adcm/entityWizard/types/wizardSlice.types';
import {
  postOperation,
  postOperationWithLastStep,
  postOperationWithStepReset,
  postOperationWithTask,
  resetSelectedStepId,
} from '@store/adcm/entityWizard/wizardActionsSlice';
import { useEntityWizardDataContext } from '../EntityWizardContextProvider/EntityWizardData.context';

interface EntityDynamicActionWizardStepProps {
  stageNumber: number;
  onClose: () => void;
}

interface SubmitStepHandlerOptions {
  isStepSkippable: boolean;
}

const EntityDynamicActionWizardStep: React.FC<EntityDynamicActionWizardStepProps> = ({
  stageNumber,
  onClose,
}: EntityDynamicActionWizardStepProps) => {
  const dispatch = useDispatch();

  const actionId = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.entityWizardActions.wizardDialog.processId);
  const process = useStore((s) => s.adcm.entityWizard.process);
  const inProgress = useStore(({ adcm }) => adcm.entityWizardActions.wizardDialog.inProgress);
  const selectedStep = useStore((s) => s.adcm.entityWizardActions.selectedStepId);
  const stepsWithData = useStore(({ adcm }) => adcm.entityWizard.steps);
  const jobsData = useStore((s) => s.adcm.entityWizard.jobsData);
  const hostComponentMapDelta = useStore(({ adcm }) => adcm.entityWizardActions.hostComponentMapDelta);
  const actionDetails = useStore(({ adcm }) => adcm.dynamicActions.actionDetails);
  const step = useStore(({ adcm }) => adcm.entityWizard.step);
  const actionHostGroup = useStore(({ adcm }) => adcm.dynamicActions.actionHostGroup);

  const { configuration } = useActionWizardConfigurationEditorContext();
  const { formData } = useActionWizardLastStageContext();
  const { entityArgs, entityType } = useEntityWizardDataContext();

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
      // (process?.stages.at(-2) - `-2` is the real last stage (the stage we manually append after the get/update process)
      // only when currentStepId > maxStepId from the real last stage -> we show imaginary last stage (which we manually appended)
      stepsWithData.length === 0 ||
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
    if ((isCurrentStepBroken || isNeedToLoadSteps) && processId && actionId && stepIds.length > 0 && actionHostGroup) {
      dispatch(
        getSteps({
          entityType,
          entityArgs,
          actionId,
          processId,
          stepIds,
          actionHostGroupId: actionHostGroup.id,
        }),
      );
    }
  }, [dispatch, stepIds, selectedStep]);

  const handleSubmitStep = (stepType: string, options?: SubmitStepHandlerOptions) => {
    if (!actionId || !process || !actionHostGroup) {
      return;
    }

    if (stepType === AdcmWizardStepType.Configuration) {
      const data = configuration[process.currentStep];
      if (!data) return;

      const payload: AdcmPostOperationPayload = {
        entityType,
        entityArgs,
        actionId,
        processId: process.id,
        actionHostGroupId: actionHostGroup.id,
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
        entityType,
        entityArgs,
        actionId,
        processId: process.id,
        actionHostGroupId: actionHostGroup.id,
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
          entityType,
          entityArgs,
          actionId,
          processId: process.id,
          stepId: process.currentStep,
          postOperationPayload: payload,
          actionHostGroupId: actionHostGroup.id,
        }),
      );
    }

    if (stepType === AdcmWizardStepType.Mapping) {
      const postMappingPayload: AdcmPostOperationPayload = {
        entityType,
        entityArgs,
        actionId,
        processId: process.id,
        actionHostGroupId: actionHostGroup.id,
        operation: {
          method: AdcmWizardMethodType.Submit,
          params: {
            stepId: process.currentStep,
            processSyncKey: process.syncKey,
            hostComponentMapDelta,
          },
        },
      };

      dispatch(postOperation(postMappingPayload));
    }

    if (stepType === AdcmWizardStepType.LastStep) {
      const postOperationPayload: AdcmPostOperationPayload = {
        entityType,
        entityArgs,
        actionId,
        processId: process.id,
        actionHostGroupId: actionHostGroup.id,
        operation: {
          method: AdcmWizardMethodType.Complete,
          params: {
            processSyncKey: process.syncKey,
          },
        },
      };

      const lastStepPayload = {
        entityType,
        entityArgs,
        actionId,
        actionHostGroupId: actionHostGroup.id,
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
    if (!actionId || !process || inProgress || !actionHostGroup) {
      return;
    }

    const postOperationPayload: AdcmPostOperationPayload = {
      entityType,
      entityArgs,
      actionId,
      processId: process.id,
      actionHostGroupId: actionHostGroup.id,
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
    if (actionId && process && currentStep && step && actionHostGroup) {
      if (isMaxStepInStage) {
        dispatch(resetStep());
      }

      if (!step.required && step.type === AdcmWizardStepType.Operation && step.state === AdcmWizardStepStates.Created) {
        handleSubmitStep(step.type, { isStepSkippable: true });
      }

      dispatch(resetSelectedStepId());
      dispatch(
        getProcess({ entityType, entityArgs, actionId, processId: process.id, actionHostGroupId: actionHostGroup.id }),
      );
    }
  };

  if (!steps || !process || processId !== process.id) return null;

  return (
    <ActionWizardSteps
      clusterId={entityArgs.clusterId}
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
      entityDynamicActionWizardOperation={EntityDynamicActionWizardOperation}
      lastStepActionDetails={actionDetails}
    />
  );
};

export default EntityDynamicActionWizardStep;
