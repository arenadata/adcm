import type React from 'react';
import { DialogV2 } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopJobWithUpdate } from '@store/adcm/jobs/jobsActionsSlice';
import JobTerminateDialogBody from '@commonComponents/job/JobTerminateDialogBody/JobTerminateDialogBody';
import { getStopJobDialogTitle } from '@commonComponents/job/jobTerminateDialogContent';

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

  const name = stopJob.displayName ?? String(stopJob.id);

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    dispatch(stopJobWithUpdate(stopJob.id));
  };

  return (
    <DialogV2
      title={getStopJobDialogTitle(name)}
      actionButtonLabel="Stop"
      onAction={handleConfirm}
      onCancel={handleClose}
    >
      <JobTerminateDialogBody />
    </DialogV2>
  );
};

export default StopJobDialog;
