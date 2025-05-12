import type React from 'react';
import s from './Dialog.module.scss';
import cn from 'classnames';
import type { ModalOptions } from '@uikit/Modal/Modal.types';
import { DialogDefaultControls, type DialogDefaultControlsProps, IconButton, Text } from '@uikit';
import Modal from '@uikit/Modal/Modal';

export interface DialogCancelConfirmationProps extends ModalOptions, DialogDefaultControlsProps {
  width?: string;
  height?: string;
  maxWidth?: string;
  minWidth?: string;
  className?: string;
  dataTest?: string;
}

const DialogCancelConfirmation: React.FC<DialogCancelConfirmationProps> = ({
  isOpen,
  onAction,
  onCancel,
  width = '584px',
  height = 'auto',
  maxWidth = '100%',
  minWidth,
  className,
  dataTest = 'dialog-cancel-confirmation-container',
}) => {
  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      onCancel?.();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={handleOpenChange}
      className={cn(s.dialog, className)}
      style={{ width, height, maxWidth, minWidth }}
      dataTest={dataTest}
    >
      <IconButton
        icon="g2-close"
        variant="secondary"
        size={24}
        className={s.dialog__close}
        onClick={onCancel}
        title="Close"
        tabIndex={-1}
      />
      <Text variant="h2" className={s.dialog__title}>
        Cancel action
      </Text>
      <div className={s.dialog__body}>Are you sure? All changes will not be saved.</div>
      <DialogDefaultControls cancelButtonLabel="No" actionButtonLabel="Yes" onAction={onAction} onCancel={onCancel} />
    </Modal>
  );
};
export default DialogCancelConfirmation;
