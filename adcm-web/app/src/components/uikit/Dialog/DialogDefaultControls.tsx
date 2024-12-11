import type React from 'react';
import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import s from './Dialog.module.scss';

export interface DialogDefaultControlsProps {
  cancelButtonLabel?: string;
  actionButtonLabel?: string;
  isActionDisabled?: boolean;
  isActionButtonLoaderShown?: boolean;
  isActionButtonDefaultFocus?: boolean;
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
}) => {
  return (
    <ButtonGroup className={s.dialog__defaultControls} data-test="dialog-control">
      <Button variant="secondary" onClick={onCancel} tabIndex={1} data-test="btn-reject">
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
  );
};
export default DialogDefaultControls;
