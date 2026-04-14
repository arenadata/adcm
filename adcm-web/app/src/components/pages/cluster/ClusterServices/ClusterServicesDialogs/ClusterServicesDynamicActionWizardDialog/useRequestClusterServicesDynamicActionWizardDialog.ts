import { useDispatch, useRequestTimer, useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { useEffect, useMemo } from 'react';
import { terminalStatuses } from '@uikit/ActionWizard/ActionWizard.constants';
import {
  getJob,
  getStep,
  loadSubJobLogFromBackend,
  refreshProcessStages,
} from '@store/adcm/cluster/services/servicesWizardSlice';

export const useRequestClusterServicesDynamicActionWizardDialog = (step: AdcmActionProcessOperationStep) => {
  const dispatch = useDispatch();
  const jobsData = useStore((s) => s.adcm.clusterServicesWizard.jobsData);

  const clusterId = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.clusterId);
  const serviceId = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.serviceId);
  const actionId = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clusterServicesWizardActions.wizardDialog.processId);
  const currentStep = useStore((s) => s.adcm.clusterServicesWizard.process)?.currentStep;
  const selectedStep = useStore((s) => s.adcm.clusterServicesWizardActions.selectedStepId);

  const jobId = (step as AdcmActionProcessOperationStep)?.task?.id;
  const stepId = step.id;
  const job = useMemo(() => (step ? jobsData[stepId]?.job : null), [step, jobsData]);
  const isJobFinished = job?.status && terminalStatuses.has(job.status);

  useEffect(() => {
    if (clusterId && serviceId && actionId && processId) {
      const stepId = selectedStep ?? currentStep;
      if (stepId) {
        dispatch(getStep({ clusterId, serviceId, actionId, processId, stepId }));
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

      if (clusterId && serviceId && actionId && processId && job?.status && terminalStatuses.has(job.status)) {
        dispatch(refreshProcessStages({ clusterId, serviceId, actionId, processId }));
      }
    }
  };

  useRequestTimer(getJobData, getJobData, requestFrequency, [step.id, step.state, job?.status]);
};
