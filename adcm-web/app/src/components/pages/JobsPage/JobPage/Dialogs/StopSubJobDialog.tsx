import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopSubJobWithUpdate } from '@store/adcm/jobs/subJobsActionsSlice';
import { useParams } from 'react-router-dom';
import { DialogV2 } from '@uikit';

const StopSubJobDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { jobId: jobIdFromUrl } = useParams();
  const jobId = Number(jobIdFromUrl);
  const subJobId = useStore(({ adcm }) => adcm.subJobsActions.stopDialog.id);
  const mode = useStore(({ adcm }) => adcm.subJobsActions.stopDialog.mode);
  const dialogDisplayName = useStore(({ adcm }) => adcm.subJobsActions.stopDialog.displayName);

  const subJob = useStore(({ adcm }) => {
    if (adcm.subJobsActions.stopDialog.id === null) {
      return null;
    }

    if (adcm.subJob.subJob?.id === adcm.subJobsActions.stopDialog.id) {
      return adcm.subJob.subJob;
    }

    return adcm.job.job?.childJobs.find(({ id }) => id === adcm.subJobsActions.stopDialog.id) ?? null;
  });

  if (subJobId === null) return null;

  const isSkip = mode === 'skip';
  const displayName = subJob?.displayName ?? dialogDisplayName ?? String(subJobId);

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    if (subJobId && jobId) {
      dispatch(stopSubJobWithUpdate({ subJobId, jobId }));
    }
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

export default StopSubJobDialog;
