import type React from 'react';
import { useDispatch, useStore } from '@hooks';
import { closeStopGroupDialog, stopJobGroupWithUpdate } from '@store/adcm/jobs/subJobsActionsSlice';
import { DialogV2 } from '@uikit';

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
      title={isSkip ? `Skip the group "${label}"` : `Terminate the group "${label}"`}
      actionButtonLabel={isSkip ? 'Skip' : 'Stop'}
      onAction={handleConfirm}
      onCancel={handleClose}
    >
      {isSkip ? 'Selected group will be skipped' : 'Selected group will be terminated'}
    </DialogV2>
  );
};

export default StopJobGroupDialog;
