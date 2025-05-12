import type React from 'react';
import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import s from './Dialog.module.scss';
import { useDialogContext } from '@uikit/DialogV2/Dialog.context';

export interface DialogDefaultControlsPropsV2 {
  onAction?: () => void;
  onCancel?: () => void;
}

const DialogDefaultControlsV2: React.FC<DialogDefaultControlsPropsV2> = ({ onAction, onCancel }) => {
  const {
    cancelButtonLabel,
    actionButtonLabel,
    isActionDisabled,
    isActionButtonLoaderShown,
    isActionButtonDefaultFocus,
    onCancel: handleCancel,
    onAction: handleAction,
  } = useDialogContext();

  return (
    <ButtonGroup className={s.dialog__defaultControls} data-test="dialog-control">
      <Button variant="secondary" onClick={onCancel ?? handleCancel} tabIndex={1} data-test="btn-reject">
        {cancelButtonLabel}
      </Button>
      <Button
        disabled={isActionDisabled}
        onClick={onAction ?? handleAction}
        data-test="btn-accept"
        iconLeft={isActionButtonLoaderShown ? { name: 'g1-load', className: 'spin' } : undefined}
        autoFocus={isActionButtonDefaultFocus}
      >
        {actionButtonLabel}
      </Button>
    </ButtonGroup>
  );
};
export default DialogDefaultControlsV2;
