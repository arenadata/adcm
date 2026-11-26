import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import { closeStopGroupDialog, stopJobGroupWithUpdate } from '@store/adcm/jobs/subJobsActionsSlice';
import { DialogV2 } from '@uikit';
import JobTerminateDialogBody from '@commonComponents/job/JobTerminateDialogBody/JobTerminateDialogBody';
import {
  getSkipGroupDialogDescription,
  getSkipGroupDialogTitle,
  getStopGroupDialogDescription,
  getStopGroupDialogTitle,
} from '@commonComponents/job/jobTerminateDialogContent';

type StopJobGroupDialogProps = {
  jobId: number;
};

const StopJobGroupDialog: React.FC<StopJobGroupDialogProps> = ({ jobId }) => {
  const dispatch = useDispatch();

  const groupName = useStore(({ adcm }) => adcm.subJobsActions.stopGroupDialog.name);
  const groupDisplayName = useStore(({ adcm }) => adcm.subJobsActions.stopGroupDialog.displayName);
  const mode = useStore(({ adcm }) => adcm.subJobsActions.stopGroupDialog.mode);

  if (!groupName) return null;

  const isSkip = mode === 'skip';
  const label = groupDisplayName ?? groupName;

  const handleClose = () => {
    dispatch(closeStopGroupDialog());
  };

  const handleConfirm = () => {
    dispatch(stopJobGroupWithUpdate({ jobId, groupName }));
  };

  return (
    <DialogV2
      title={isSkip ? getSkipGroupDialogTitle(label) : getStopGroupDialogTitle(label)}
      actionButtonLabel={isSkip ? 'Skip' : 'Stop'}
      onAction={handleConfirm}
      onCancel={handleClose}
    >
      <JobTerminateDialogBody
        description={isSkip ? getSkipGroupDialogDescription(label) : getStopGroupDialogDescription(label)}
      />
    </DialogV2>
  );
};

export default StopJobGroupDialog;
