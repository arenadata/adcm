import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopSubJobWithUpdate } from '@store/adcm/jobs/subJobsActionsSlice';
import { useParams } from 'react-router-dom';
import { Dialog } from '@uikit';

const StopSubJobDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { jobId: jobIdFromUrl } = useParams();
  const jobId = Number(jobIdFromUrl);

  const subJob = useStore(({ adcm }) => {
    // when stop on SubJobPage
    if (adcm.subJob.subJob?.id === adcm.subJobsActions.stopDialog.id) {
      return adcm.subJob.subJob;
    }

    // when stop on JobPage
    return adcm.job.job?.childJobs.find(({ id }) => id === adcm.subJobsActions.stopDialog.id) ?? null;
  });

  const handleClose = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirm = () => {
    if (subJob?.id && jobId) {
      dispatch(stopSubJobWithUpdate({ subJobId: subJob.id, jobId }));
    }
  };

  return (
    <Dialog
      //
      isOpen={!!subJob}
      title={`Terminate the subjob "${subJob?.displayName}"`}
      actionButtonLabel="Stop"
      onAction={handleConfirm}
      onOpenChange={handleClose}
    >
      Selected subjob will be terminated
    </Dialog>
  );
};

export default StopSubJobDialog;
