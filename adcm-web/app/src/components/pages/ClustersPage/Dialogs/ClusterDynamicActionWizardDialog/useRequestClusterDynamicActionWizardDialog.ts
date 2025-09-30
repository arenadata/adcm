import { useDispatch, useRequestTimer, useStore } from '@hooks';
import { resetJobData, getStep, getSubJob, refreshProcessStages } from '@store/adcm/clusters/clustersWizardSlice';
import { getJob } from '@store/adcm/clusters/clustersWizardSlice';
import type { AdcmActionProcessOperationStep } from '@models/adcm/wizard';
import { AdcmJobStatus } from '@models/adcm';
import { useEffect, useMemo } from 'react';

export const useRequestClusterDynamicActionWizardDialog = () => {
  const dispatch = useDispatch();
  const job = useStore((s) => s.adcm.clustersWizard.job);
  const step = useStore((s) => s.adcm.clustersWizard.step);

  const clusterId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.clusterId);
  const actionId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.actionId);
  const processId = useStore((s) => s.adcm.clustersWizardActions.wizardDialog.process)?.id;
  const selectedStep = useStore((s) => s.adcm.clustersWizardActions.selectedStepId);

  useEffect(() => {
    if (clusterId && actionId && processId && selectedStep) {
      dispatch(resetJobData());
      dispatch(getStep({ clusterId, actionId, processId, stepId: selectedStep }));
    }
  }, [dispatch, selectedStep]);

  const requestFrequency = useMemo(() => {
    return job?.status === AdcmJobStatus.Success ? 0 : 3;
  }, [job?.status]);

  const getJobData = () => {
    if (step && (step as AdcmActionProcessOperationStep).task) {
      if (job?.status !== AdcmJobStatus.Success) {
        dispatch(getJob());

        if (job) {
          dispatch(getSubJob(job.id));
        }
      } else {
        if (clusterId && actionId && processId) {
          dispatch(refreshProcessStages({ clusterId, actionId, processId }));
        }
      }
    }
  };

  useRequestTimer(getJobData, getJobData, requestFrequency, [step, job?.status]);
};
