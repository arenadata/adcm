import type React from 'react';
import { useState } from 'react';
import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import s from './Dialog.module.scss';
import DialogCancelConfirmation from '@uikit/Dialog/DialogCancelConfirmation';

export interface DialogDefaultControlsProps {
  cancelButtonLabel?: string;
  actionButtonLabel?: string;
  isActionDisabled?: boolean;
  isActionButtonLoaderShown?: boolean;
  isActionButtonDefaultFocus?: boolean;
  isNeedConfirmationOnCancel?: boolean;
  onAction?: () => void;
  onCancel?: () => void;
}

const DialogDefaultControls: React.FC<DialogDefaultControlsProps> = ({
  actionButtonLabel = 'Run',
  onAction,
  cancelButtonLabel = 'Cancel',
  onCancel,
  isActionDisabled = false,
  isActionButtonLoaderShown = false,
  isActionButtonDefaultFocus = false,
  isNeedConfirmationOnCancel = false,
}) => {
  const [isOpenConfirmationDialog, setIsOpenConfirmationDialog] = useState(false);

  const handleCancel = () => {
    if (isNeedConfirmationOnCancel) {
      setIsOpenConfirmationDialog(true);
    } else {
      onCancel?.();
    }
  };

  const handleConfirmationAction = () => {
    setIsOpenConfirmationDialog(false);
    onCancel?.();
  };

  const handleConfirmationCancel = () => {
    setIsOpenConfirmationDialog(false);
  };

  return (
    <>
      <ButtonGroup className={s.dialog__defaultControls} data-test="dialog-control">
        <Button variant="secondary" onClick={handleCancel} tabIndex={1} data-test="btn-reject">
          {cancelButtonLabel}
        </Button>
        <Button
          disabled={isActionDisabled}
          onClick={onAction}
          data-test="btn-accept"
          iconLeft={isActionButtonLoaderShown ? { name: 'g1-load', className: 'spin' } : undefined}
          autoFocus={isActionButtonDefaultFocus}
        >
          {actionButtonLabel}
        </Button>
      </ButtonGroup>
      {isNeedConfirmationOnCancel && (
        <DialogCancelConfirmation
          isOpen={isOpenConfirmationDialog}
          onOpenChange={handleConfirmationCancel}
          onAction={handleConfirmationAction}
          onCancel={handleConfirmationCancel}
        />
      )}
    </>
  );
};
export default DialogDefaultControls;
