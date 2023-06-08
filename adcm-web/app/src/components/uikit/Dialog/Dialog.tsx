import React from 'react';
import Modal from '@uikit/Modal/Modal';
import { ModalOptions } from '@uikit/Modal/Modal.types';
import IconButton from '@uikit/IconButton/IconButton';
import Text from '@uikit/Text/Text';
import { DialogControlsOptions } from '@uikit/Dialog/Dialog.types';
import DialogDefaultControls from '@uikit/Dialog/DialogDefaultControls';
import s from './Dialog.module.scss';

export interface DialogProps extends ModalOptions, DialogControlsOptions {
  children: React.ReactNode;
  title?: React.ReactNode;
  dialogControls?: React.ReactNode;
  width?: string;
}
const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onOpenChange,
  isDismissDisabled,
  children,
  title,
  dialogControls,
  cancelButtonLabel,
  actionButtonLabel,
  isActionDisabled,
  onAction,
  onCancel,
  width = '584px',
}) => {
  const handleClose = () => {
    onOpenChange(false);
    onCancel?.();
  };

  const handleIsOpenChange = (isOpen: boolean) => {
    // we can't open Dialog from Dialog, we can close Dialog only
    if (!isOpen) {
      handleClose();
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={handleIsOpenChange}
      className={s.dialog}
      isDismissDisabled={isDismissDisabled}
      style={{ width }}
    >
      <IconButton
        icon="g2-close"
        variant="secondary"
        size={24}
        className={s.dialog__close}
        onClick={handleClose}
        title="Close"
      />
      {title && (
        <Text variant="h2" className={s.dialog__title}>
          {title}
        </Text>
      )}
      <div className={s.dialog__body}>{children}</div>
      {dialogControls ?? (
        <DialogDefaultControls
          cancelButtonLabel={cancelButtonLabel}
          actionButtonLabel={actionButtonLabel}
          isActionDisabled={isActionDisabled}
          onAction={onAction}
          onCancel={handleClose}
        />
      )}
    </Modal>
  );
};
export default Dialog;
