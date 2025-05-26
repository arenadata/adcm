import type React from 'react';
import DialogV2 from '@uikit/DialogV2/Dialog';

export interface ConfigurationEditorDialogProps extends React.PropsWithChildren {
  triggerRef: React.RefObject<HTMLElement>;
  width?: string;
  maxWidth?: string;
  isApplyDisabled: boolean;
  onCancel: () => void;
  onApply: () => void;
}

const ConfigurationEditorDialog = ({
  children,
  width = '640px',
  maxWidth = '100%',
  isApplyDisabled,
  onCancel,
  onApply,
}: ConfigurationEditorDialogProps) => {
  return (
    <DialogV2
      width={width}
      maxWidth={maxWidth}
      onCancel={onCancel}
      onAction={onApply}
      isActionDisabled={isApplyDisabled}
      buttonInControlWithFocus={null}
      cancelButtonLabel="Cancel"
      actionButtonLabel="Apply"
    >
      {children}
    </DialogV2>
  );
};

export default ConfigurationEditorDialog;
