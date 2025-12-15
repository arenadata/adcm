import { useDispatch, useRequestTimer, useStore } from '@hooks';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { useEffect, useMemo } from 'react';
import { terminalStatuses } from '@uikit/ActionWizard/ActionWizard.constants';
import {
  getJob,
  getStep,
  loadSubJobLogFromBackend,
  refreshProcessStages,
} from '@store/adcm/cluster/services/serviceComponents/serviceComponentsWizardSlice';

export const useRequestServiceComponentsDynamicActionWizardDialog = (step: AdcmActionProcessOperationStep) => {
  const dispatch = useDispatch();
  const jobsData = useStore((s) => s.adcm.clustersWizard.jobsData);

  const clusterId = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.clusterId);
  const serviceId = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.serviceId);
  const componentId = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.componentId);
  const actionId = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.wizardDialog.processId);
  const currentStep = useStore((s) => s.adcm.clusterServiceComponentsWizard.process)?.currentStep;
  const selectedStep = useStore((s) => s.adcm.clusterServiceComponentsWizardActions.selectedStepId);

  useEffect(() => {
    if (clusterId && serviceId && componentId && actionId && processId) {
      const stepId = selectedStep ?? currentStep;
      if (stepId) {
        dispatch(getStep({ clusterId, serviceId, componentId, actionId, processId, stepId }));
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

      if (
        clusterId &&
        serviceId &&
        componentId &&
        actionId &&
        processId &&
        job?.status &&
        terminalStatuses.has(job.status)
      ) {
        dispatch(refreshProcessStages({ clusterId, serviceId, componentId, actionId, processId }));
      }
    }
  };

  useRequestTimer(getJobData, getJobData, requestFrequency, [step.id, step.state, job?.status]);
};
