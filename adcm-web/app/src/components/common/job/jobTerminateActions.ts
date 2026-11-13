import { AdcmJobStatus } from '@models/adcm';

type TerminatableEntity = {
  isTerminatable: boolean;
  status: AdcmJobStatus;
};

export const getJobTerminateActions = ({ isTerminatable, status }: TerminatableEntity) => ({
  isSkipEnabled: isTerminatable && status === AdcmJobStatus.Created,
  isStopEnabled: isTerminatable && status === AdcmJobStatus.Running,
});
