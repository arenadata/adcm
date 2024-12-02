import { useMemo, useState } from 'react';
import { useDebounce, useDispatch, useRequestTimer, useStore } from '@hooks';
import { getSubJobLog } from '@store/adcm/jobs/subJobSlice';
import { defaultDebounceDelay } from '@constants';
import { AdcmJobStatus } from '@models/adcm';

const maxUpdatesAfterFinishCount = 2;

const finishedStatuses: { [key in AdcmJobStatus]: boolean } = {
  [AdcmJobStatus.Created]: false,
  [AdcmJobStatus.Success]: true,
  [AdcmJobStatus.Failed]: true,
  [AdcmJobStatus.Running]: false,
  [AdcmJobStatus.Locked]: true,
  [AdcmJobStatus.Aborted]: true,
  [AdcmJobStatus.Broken]: true,
};

export const useRequestSubJobLogs = () => {
  const dispatch = useDispatch();
  const subJob = useStore(({ adcm }) => adcm.subJob.subJob);
  const requestFrequency = useStore(({ adcm }) => adcm.jobsTable.requestFrequency);
  const [updatesAfterFinishCount, setUpdatedAfterFinishCount] = useState(0);

  const debounceGetData = useDebounce(() => {
    if (subJob) {
      dispatch(getSubJobLog(subJob.id));

      if (finishedStatuses[subJob.status]) {
        setUpdatedAfterFinishCount((prevState) => prevState + 1);
      }
    }
  }, defaultDebounceDelay);

  const isNeedUpdate = useMemo(
    () => subJob && updatesAfterFinishCount < maxUpdatesAfterFinishCount,
    [subJob, updatesAfterFinishCount],
  );

  useRequestTimer(debounceGetData, debounceGetData, isNeedUpdate ? requestFrequency : 0, [subJob?.id]);
};
