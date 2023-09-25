import React from 'react';
import Modal from '@uikit/Modal/Modal';
import { ModalOptions } from '@uikit/Modal/Modal.types';
import IconButton from '@uikit/IconButton/IconButton';
import Text from '@uikit/Text/Text';
import DialogDefaultControls, { DialogDefaultControlsProps } from '@uikit/Dialog/DialogDefaultControls';
import s from './Dialog.module.scss';

export interface DialogProps extends ModalOptions, DialogDefaultControlsProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  dialogControls?: React.ReactNode;
  dialogControlsOnTop?: boolean;
  width?: string;
  height?: string;
}

const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onOpenChange,
  isDismissDisabled,
  children,
  title,
  dialogControls,
  dialogControlsOnTop,
  cancelButtonLabel,
  actionButtonLabel,
  isActionDisabled,
  onAction,
  onCancel,
  width = '584px',
  height = 'auto',
}) => {
  const handleClose = () => {
    onOpenChange(false);
    onCancel?.();
  };

  const handleOpenChange = (isOpen: boolean) => {
    // we can't open Dialog from Dialog, we can close Dialog only
    if (!isOpen) {
      handleClose();
    }
  };

  const dialogControlsComponent = dialogControls || (
    <DialogDefaultControls
      cancelButtonLabel={cancelButtonLabel}
      actionButtonLabel={actionButtonLabel}
      isActionDisabled={isActionDisabled}
      onAction={onAction}
      onCancel={handleClose}
    />
  );

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={handleOpenChange}
      className={s.dialog}
      isDismissDisabled={isDismissDisabled}
      style={{ width, height }}
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
      {dialogControlsOnTop && dialogControlsComponent}
      <div className={s.dialog__body}>{children}</div>
      {!dialogControlsOnTop && dialogControlsComponent}
    </Modal>
  );
};
export default Dialog;
