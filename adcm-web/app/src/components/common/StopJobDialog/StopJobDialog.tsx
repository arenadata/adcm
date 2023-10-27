import { Dialog } from '@uikit';
import React from 'react';

interface StopJobDialogProps {
  title: string;
  isOpen: boolean;
  onOpenChange: () => void;
  onAction: () => void;
}

const StopJobDialog: React.FC<StopJobDialogProps> = ({ title, isOpen, onOpenChange, onAction }) => {
  return (
    <Dialog
      //
      isOpen={isOpen}
      onOpenChange={onOpenChange}
      title={title}
      onAction={onAction}
      actionButtonLabel="Stop"
    >
      Selected job will be terminated
    </Dialog>
  );
};

export default StopJobDialog;
