import type React from 'react';
import { useState } from 'react';
import Modal from '@uikit/Modal/Modal';
import type { ModalOptions } from '@uikit/Modal/Modal.types';
import IconButton from '@uikit/IconButton/IconButton';
import Text from '@uikit/Text/Text';
import type { DialogDefaultControlsProps } from '@uikit/Dialog/DialogDefaultControls';
import DialogDefaultControls from '@uikit/Dialog/DialogDefaultControls';
import Panel from '@uikit/Panel/Panel';
import s from './Dialog.module.scss';
import cn from 'classnames';
import DialogCancelConfirmation from '@uikit/Dialog/DialogCancelConfirmation';

export interface DialogProps extends ModalOptions, DialogDefaultControlsProps {
  children: React.ReactNode;
  title?: React.ReactNode;
  dialogControls?: React.ReactNode;
  isActionButtonDefaultFocus?: boolean;
  isDialogControlsOnTop?: boolean;
  width?: string;
  height?: string;
  maxWidth?: string;
  minWidth?: string;
  className?: string;
  dataTest?: string;
}

const Dialog: React.FC<DialogProps> = ({
  isOpen,
  onOpenChange,
  isDismissDisabled,
  children,
  title,
  dialogControls,
  isActionButtonDefaultFocus,
  isDialogControlsOnTop,
  cancelButtonLabel,
  actionButtonLabel,
  isActionButtonLoaderShown,
  isActionDisabled,
  isNeedConfirmationOnCancel = false,
  onAction,
  onCancel,
  width = '584px',
  height = 'auto',
  maxWidth = '100%',
  minWidth,
  className,
  dataTest = 'dialog-container',
}) => {
  const [isOpenConfirmationDialog, setIsOpenConfirmationDialog] = useState(false);

  const handleClose = () => {
    if (isNeedConfirmationOnCancel) {
      setIsOpenConfirmationDialog(true);
    } else {
      onOpenChange(false);
      onCancel?.();
    }
  };

  const handleOpenChange = (isOpen: boolean) => {
    // we can't open Dialog from Dialog, we can close Dialog only
    if (!isOpen) {
      handleClose();
    }
  };

  const handleConfirmationCancel = () => {
    setIsOpenConfirmationDialog(false);
  };

  const handleConfirmationAction = () => {
    setIsOpenConfirmationDialog(false);
    onOpenChange(false);
    onCancel?.();
  };

  const dialogControlsComponent = dialogControls ?? (
    <DialogDefaultControls
      cancelButtonLabel={cancelButtonLabel}
      actionButtonLabel={actionButtonLabel}
      isActionDisabled={isActionDisabled}
      isActionButtonLoaderShown={isActionButtonLoaderShown}
      onAction={onAction}
      onCancel={handleClose}
      isActionButtonDefaultFocus={isActionButtonDefaultFocus}
      isNeedConfirmationOnCancel={isNeedConfirmationOnCancel}
    />
  );

  return (
    <Modal
      isOpen={isOpen}
      onOpenChange={handleOpenChange}
      className={cn(s.dialog, className)}
      isDismissDisabled={isDismissDisabled}
      style={{ width, height, maxWidth, minWidth }}
      dataTest={dataTest}
    >
      <IconButton
        icon="g2-close"
        variant="secondary"
        size={24}
        className={s.dialog__close}
        onClick={handleClose}
        title="Close"
        tabIndex={-1}
      />
      {title && (
        <Text variant="h2" className={s.dialog__title}>
          {title}
        </Text>
      )}
      {isDialogControlsOnTop && dialogControlsComponent && (
        <Panel className={s.dialog__controlsOnTop} variant="primary">
          {dialogControlsComponent}
        </Panel>
      )}
      <div className={s.dialog__body}>{children}</div>
      {!isDialogControlsOnTop && dialogControlsComponent}
      {isNeedConfirmationOnCancel && (
        <DialogCancelConfirmation
          isOpen={isOpenConfirmationDialog}
          onOpenChange={handleConfirmationCancel}
          onAction={handleConfirmationAction}
          onCancel={handleConfirmationCancel}
        />
      )}
    </Modal>
  );
};
export default Dialog;
