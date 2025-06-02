import type React from 'react';
import { DialogV2 } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopJobWithUpdate } from '@store/adcm/jobs/jobsActionsSlice';

const StopJobDialog: React.FC = () => {
  const dispatch = useDispatch();

  const stopJob = useStore(
    ({
      adcm: {
        jobs: { jobs },
        jobsActions: {
          stopDialog: { id: itemId },
        },
      },
    }) => {
      if (!itemId) return null;
      return jobs.find(({ id }) => id === itemId) ?? null;
    },
  );

  if (!stopJob) return null;

  const name = stopJob?.displayName;

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    if (!stopJob?.id) return;

    dispatch(stopJobWithUpdate(stopJob.id));
  };

  return (
    <DialogV2
      //
      title={`Terminate the job "${name}"`}
      actionButtonLabel="Stop"
      onAction={handleConfirm}
      onCancel={handleClose}
    >
      Selected job will be terminated
    </DialogV2>
  );
};

export default StopJobDialog;
