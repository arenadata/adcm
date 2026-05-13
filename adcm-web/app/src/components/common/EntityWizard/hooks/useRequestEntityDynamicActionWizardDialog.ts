import { useDispatch, useRequestTimer, useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { useCallback, useEffect, useMemo } from 'react';
import { terminalStatuses } from '@uikit/ActionWizard/ActionWizard.constants';
import type { EntityArgs, WizardOwner } from '@store/adcm/entityWizard/types/wizardSlice.types';
import { getJob, getStep, loadSubJobLogFromBackend, refreshProcessStages } from '@store/adcm/entityWizard/wizardSlice';
import { defaultRequestFrequency, zeroRequestFrequency } from '@constants';

export const useRequestEntityDynamicActionWizardDialog = <T extends WizardOwner>(
  entityType: T,
  entityArgs: EntityArgs<T>,
  step: AdcmActionProcessOperationStep,
) => {
  const dispatch = useDispatch();
  const jobsData = useStore((s) => s.adcm.entityWizard.jobsData);
  const currentStep = useStore((s) => s.adcm.entityWizard.process)?.currentStep;

  const actionId = useStore((s) => s.adcm.entityWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.entityWizardActions.wizardDialog.processId);
  const selectedStep = useStore((s) => s.adcm.entityWizardActions.selectedStepId);

  const jobId = (step as AdcmActionProcessOperationStep)?.task?.id;
  const stepId = step.id;
  const job = useMemo(() => (step ? jobsData[stepId]?.job : null), [step, jobsData]);
  const isJobFinished = job?.status && terminalStatuses.has(job.status);
  const actionHostGroup = useStore(({ adcm }) => adcm.dynamicActions.actionHostGroup);

  useEffect(() => {
    if (actionId && processId && actionHostGroup) {
      const stepId = selectedStep ?? currentStep;
      if (stepId) {
        dispatch(
          getStep({
            entityType,
            entityArgs,
            actionId,
            processId,
            stepId,
            actionHostGroupId: actionHostGroup.id,
          }),
        );
      }
    }
  }, [dispatch, actionId, processId, selectedStep, currentStep, isJobFinished]);

  const requestFrequency = isJobFinished ? zeroRequestFrequency : defaultRequestFrequency;

  const getJobData = useCallback(() => {
    if (jobId && currentStep && step.id <= currentStep && actionHostGroup) {
      dispatch(getJob({ jobId, stepId }));

      if (job) {
        const subJobIds = job.childJobs.map((childJob) => childJob.id);

        dispatch(loadSubJobLogFromBackend({ subJobIds, stepId }));
      }

      if (actionId && processId && job?.status && terminalStatuses.has(job.status)) {
        dispatch(
          refreshProcessStages({ entityType, entityArgs, actionId, processId, actionHostGroupId: actionHostGroup.id }),
        );
      }
    }
  }, [jobId, currentStep, step.id, job, actionId, processId]);

  useRequestTimer(getJobData, getJobData, requestFrequency, [step.id, step.state, job?.status]);
};
