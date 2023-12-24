import React from 'react';
import StopJobDialog from '@commonComponents/StopJobDialog/StopJobDialog';
import { useDispatch, useStore } from '@hooks';
import { closeStopDialog, stopChildJobWithUpdate } from '@store/adcm/jobs/jobsActionsSlice';
import { useParams } from 'react-router-dom';

const JobPageStopJobDialog: React.FC = () => {
  const dispatch = useDispatch();
  const { jobId: jobIdFromUrl } = useParams();
  const jobId = Number(jobIdFromUrl);

  const childJob = useStore(({ adcm }) => {
    return adcm.jobs.task.childJobs.find(({ id }) => id === adcm.jobsActions.stopDialog.id) ?? null;
  });

  const handleCloseConfirm = () => {
    dispatch(closeStopDialog());
  };

  const handleConfirmDialog = () => {
    if (childJob?.id && jobId) {
      dispatch(stopChildJobWithUpdate({ childJobId: childJob.id, jobId }));
    }
  };

  return (
    <StopJobDialog
      isOpen={!!childJob}
      title={`Terminate the job "${childJob?.displayName}"`}
      onAction={handleConfirmDialog}
      onOpenChange={handleCloseConfirm}
    />
  );
};

export default JobPageStopJobDialog;
