import { useDispatch, useStore } from '@hooks';
import { closeRestartDialog, restartJobWithUpdate } from '@store/adcm/jobs/jobsActionsSlice';
import { Dialog } from '@uikit';
import React from 'react';

const JobsRestartDialog: React.FC = () => {
  const dispatch = useDispatch();

  const restartJob = useStore(
    ({
      adcm: {
        jobs: { jobs },
        jobsActions: {
          restartDialog: { id: restartId },
        },
      },
    }) => {
      if (!restartId) return null;
      return jobs.find(({ id }) => id === restartId) ?? null;
    },
  );

  const isOpenDialog = !!restartJob;
  const name = restartJob?.name;

  const handleCloseConfirm = () => {
    dispatch(closeRestartDialog());
  };

  const handleConfirmDialog = () => {
    if (!restartJob?.id) return;

    dispatch(restartJobWithUpdate(restartJob.id));
  };

  return (
    <Dialog
      isOpen={isOpenDialog}
      onOpenChange={handleCloseConfirm}
      title={`Restart job "${name}"`}
      onAction={handleConfirmDialog}
      actionButtonLabel="Restart"
    >
      Job will be restarted.
    </Dialog>
  );
};

export default JobsRestartDialog;
