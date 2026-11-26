import { AdcmJobStatus } from '@models/adcm';

type TerminatableEntity = {
  isTerminatable: boolean;
  status: AdcmJobStatus;
};

const SUBJOB_STOP_STATUSES = new Set([AdcmJobStatus.Scheduled, AdcmJobStatus.Running]);

const PARENT_JOB_STOP_STATUSES = new Set([AdcmJobStatus.Created, AdcmJobStatus.Scheduled, AdcmJobStatus.Running]);

export const getJobTerminateActions = ({ isTerminatable, status }: TerminatableEntity) => ({
  isSkipEnabled: isTerminatable && status === AdcmJobStatus.Created,
  isStopEnabled: isTerminatable && SUBJOB_STOP_STATUSES.has(status),
});

export const isParentJobStopEnabled = ({ isTerminatable, status }: TerminatableEntity) =>
  isTerminatable && PARENT_JOB_STOP_STATUSES.has(status);
