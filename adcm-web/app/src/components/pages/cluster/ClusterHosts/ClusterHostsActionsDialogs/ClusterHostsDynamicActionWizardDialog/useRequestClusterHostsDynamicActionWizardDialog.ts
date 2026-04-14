import { useDispatch, useRequestTimer, useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { useEffect, useMemo } from 'react';
import {
  getJob,
  getStep,
  loadSubJobLogFromBackend,
  refreshProcessStages,
} from '@store/adcm/cluster/hosts/hostsWizardSlice';
import { terminalStatuses } from '@uikit/ActionWizard/ActionWizard.constants';

export const useRequestClusterHostsDynamicActionWizardDialog = (step: AdcmActionProcessOperationStep) => {
  const dispatch = useDispatch();
  const jobsData = useStore((s) => s.adcm.clusterHostsWizard.jobsData);

  const clusterId = useStore((s) => s.adcm.clusterHostsWizardActions.wizardDialog.clusterId);
  const hostId = useStore((s) => s.adcm.clusterHostsWizardActions.wizardDialog.hostId);
  const actionId = useStore((s) => s.adcm.clusterHostsWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clusterHostsWizardActions.wizardDialog.processId);
  const currentStep = useStore((s) => s.adcm.clusterHostsWizard.process)?.currentStep;
  const selectedStep = useStore((s) => s.adcm.clusterHostsWizardActions.selectedStepId);

  const jobId = (step as AdcmActionProcessOperationStep)?.task?.id;
  const stepId = step.id;
  const job = useMemo(() => (step ? jobsData[stepId]?.job : null), [step, jobsData]);
  const isJobFinished = job?.status && terminalStatuses.has(job.status);

  useEffect(() => {
    if (clusterId && hostId && actionId && processId) {
      const stepId = selectedStep ?? currentStep;
      if (stepId) {
        dispatch(getStep({ clusterId, hostId, actionId, processId, stepId }));
      }
    }
  }, [dispatch, selectedStep, currentStep, isJobFinished]);

  const requestFrequency = isJobFinished ? 0 : 3;

  const getJobData = () => {
    if (jobId && currentStep && step.id <= currentStep) {
      dispatch(getJob({ jobId, stepId }));

      if (job) {
        const subJobIds = job.childJobs.map((childJob) => childJob.id);
        dispatch(loadSubJobLogFromBackend({ subJobIds, stepId }));
      }

      if (clusterId && hostId && actionId && processId && job?.status && terminalStatuses.has(job.status)) {
        dispatch(refreshProcessStages({ clusterId, hostId, actionId, processId }));
      }
    }
  };

  useRequestTimer(getJobData, getJobData, requestFrequency, [step.id, step.state, job?.status]);
};
