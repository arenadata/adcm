import React from 'react';
import Button from '@uikit/Button/Button';
import ButtonGroup from '@uikit/ButtonGroup/ButtonGroup';
import { DialogControlsOptions } from './Dialog.types';
import s from './Dialog.module.scss';

const DialogDefaultControls: React.FC<DialogControlsOptions> = ({
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
