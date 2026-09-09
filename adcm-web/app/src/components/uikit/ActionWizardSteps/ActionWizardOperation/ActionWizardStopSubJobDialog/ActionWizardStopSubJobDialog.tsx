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
  const subJob = job.childJobs.find(({ id }) => id === stopDialogId) ?? null;

  if (!subJob) return null;

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    dispatch(stopSubJobWithUpdate({ subJobId: subJob.id, jobId: job.id }));
  };

  return (
    <DialogV2
      //
      title={`Terminate the subjob "${subJob.displayName}"`}
      actionButtonLabel="Stop"
      onAction={handleConfirm}
      onCancel={handleClose}
    >
      Selected subjob will be terminated
    </DialogV2>
  );
};

export default ActionWizardStopSubJobDialog;
