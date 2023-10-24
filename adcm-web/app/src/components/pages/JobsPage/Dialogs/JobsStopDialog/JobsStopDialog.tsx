import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopJobWithUpdate } from '@store/adcm/jobs/jobsActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const JobsStopDialog: React.FC = () => {
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

  const isOpenDialog = !!stopJob;
  const name = stopJob?.displayName;

  const handleCloseConfirm = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirmDialog = () => {
    if (!stopJob?.id) return;

    dispatch(stopJobWithUpdate(stopJob.id));
  };

  return (
    <Dialog
      isOpen={isOpenDialog}
      onOpenChange={handleCloseConfirm}
      title={`Terminate the job "${name}"`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Stop"
    >
      Selected job will be terminated
    </Dialog>
  );
};

export default JobsStopDialog;
