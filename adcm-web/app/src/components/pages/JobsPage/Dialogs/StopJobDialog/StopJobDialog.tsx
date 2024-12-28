import type React from 'react';
import { Dialog } from '@uikit';
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

  const name = stopJob?.displayName;

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    if (!stopJob?.id) return;

    dispatch(stopJobWithUpdate(stopJob.id));
  };

  return (
    <Dialog
      //
      title={`Terminate the job "${name}"`}
      isOpen={!!stopJob}
      actionButtonLabel="Stop"
      onAction={handleConfirm}
      onOpenChange={handleClose}
    >
      Selected job will be terminated
    </Dialog>
  );
};

export default StopJobDialog;
