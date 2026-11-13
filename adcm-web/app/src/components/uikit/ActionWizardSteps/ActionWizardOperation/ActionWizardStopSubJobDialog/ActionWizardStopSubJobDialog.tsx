import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopSubJobWithUpdate } from '@store/adcm/jobs/subJobsActionsSlice';
import { DialogV2 } from '@uikit';
import type { AdcmJob } from '@models/adcm';

interface ActionWizardStopSubJobDialogProps {
  job: AdcmJob;
}

const ActionWizardStopSubJobDialog: React.FC<ActionWizardStopSubJobDialogProps> = ({ job }) => {
  const dispatch = useDispatch();

  const stopDialogId = useStore(({ adcm }) => adcm.subJobsActions.stopDialog.id);
  const mode = useStore(({ adcm }) => adcm.subJobsActions.stopDialog.mode);
  const dialogDisplayName = useStore(({ adcm }) => adcm.subJobsActions.stopDialog.displayName);
  const subJob = job.childJobs.find(({ id }) => id === stopDialogId) ?? null;

  if (stopDialogId === null) return null;

  const isSkip = mode === 'skip';
  const displayName = subJob?.displayName ?? dialogDisplayName ?? String(stopDialogId);

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    dispatch(stopSubJobWithUpdate({ subJobId: stopDialogId, jobId: job.id }));
  };

  return (
    <DialogV2
      title={isSkip ? `Skip the subjob "${displayName}"` : `Terminate the subjob "${displayName}"`}
      actionButtonLabel={isSkip ? 'Skip' : 'Stop'}
      onAction={handleConfirm}
      onCancel={handleClose}
    >
      {isSkip ? 'Selected subjob will be skipped' : 'Selected subjob will be terminated'}
    </DialogV2>
  );
};

export default ActionWizardStopSubJobDialog;
