import { useDispatch, useRequestTimer, useStore } from '@hooks';
import { getStep, loadSubJobLogFromBackend, refreshProcessStages } from '@store/adcm/clusters/clustersWizardSlice';
import { getJob } from '@store/adcm/clusters/clustersWizardSlice';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { AdcmJobStatus } from '@models/adcm';
import { useEffect, useMemo } from 'react';

const terminalStatuses = new Set([
  AdcmJobStatus.Success,
  AdcmJobStatus.Failed,
  AdcmJobStatus.Locked,
  AdcmJobStatus.Aborted,
  AdcmJobStatus.Broken,
]);

export const useRequestClusterDynamicActionWizardDialog = (step: AdcmActionProcessOperationStep) => {
  const dispatch = useDispatch();
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);

  const clusterId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.clusterId);
  const actionId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.processId);
  const currentStep = useStore((s) => s.adcm.clustersWizard.process)?.currentStep;
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);

  useEffect(() => {
    if (clusterId && actionId && processId) {
      const stepId = selectedStep ?? currentStep;
      if (stepId) {
        dispatch(getStep({ clusterId, actionId, processId, stepId }));
      }
    }
  }, [dispatch, selectedStep, currentStep]);

  const jobId = (step as AdcmActionProcessOperationStep)?.task?.id;
  const stepId = step.id;
  const job = useMemo(() => (step ? jobsData[stepId]?.job : null), [step, jobsData]);
  const requestFrequency = useMemo(() => (job?.status && terminalStatuses.has(job.status) ? 0 : 3), [job?.status]);

  const getJobData = () => {
    if (jobId && currentStep && step.id <= currentStep) {
      dispatch(getJob({ jobId, stepId }));

      if (job) {
        const subJobIds = job.childJobs.map((childJob) => childJob.id);
        dispatch(loadSubJobLogFromBackend({ subJobIds, stepId }));
      }

      if (clusterId && actionId && processId && job?.status && terminalStatuses.has(job.status)) {
        dispatch(refreshProcessStages({ clusterId, actionId, processId }));
      }
    }
  };

  useRequestTimer(getJobData, getJobData, requestFrequency, [step.id, step.state, job?.status]);
};
