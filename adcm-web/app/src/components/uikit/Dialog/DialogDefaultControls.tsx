import React from 'react';
import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import s from './Dialog.module.scss';

export interface DialogDefaultControlsProps {
  cancelButtonLabel?: string;
  actionButtonLabel?: string;
  isActionDisabled?: boolean;
  onAction?: () => void;
  onCancel?: () => void;
}

const DialogDefaultControls: React.FC<DialogDefaultControlsProps> = ({
  actionButtonLabel = 'Run',
  onAction,
  cancelButtonLabel = 'Cancel',
  onCancel,
  isActionDisabled = false,
}) => {
  return (
    <ButtonGroup className={s.dialog__defaultControls}>
      <Button variant="secondary" onClick={onCancel}>
        {cancelButtonLabel}
      </Button>
      <Button disabled={isActionDisabled} onClick={onAction}>
        {actionButtonLabel}
      </Button>
    </ButtonGroup>
  );
};
export default DialogDefaultControls;
