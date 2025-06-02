import type React from 'react';
import { useState } from 'react';
import s from '@uikit/DialogV2/Dialog.module.scss';
import cn from 'classnames';
import { DialogContext } from './Dialog.context';
import IconButton from '@uikit/IconButton/IconButton';
import DialogDefaultControlsV2 from './DialogDefaultControls';
import Text from '@uikit/Text/Text';
import Modal from '@uikit/Modal/Modal';

export type ButtonsInControl = null | 'action' | 'cancel';

export interface DialogV2Props {
  children: React.ReactNode;
  title?: React.ReactNode;
  dialogControls?: React.ReactNode;
  isDialogControlsOnTop?: boolean;
  width?: string;
  height?: string;
  maxWidth?: string;
  minWidth?: string;
  className?: string;
  dataTest?: string;
  cancelButtonLabel?: string;
  actionButtonLabel?: string;
  isActionDisabled?: boolean;
  isActionButtonLoaderShown?: boolean;
  isNeedConfirmationOnCancel?: boolean;
  buttonInControlWithFocus?: ButtonsInControl;
  onAction?: () => void;
  onCancel: () => void;
}

const DialogV2: React.FC<DialogV2Props> = ({
  children,
  title,
  dialogControls,
  isDialogControlsOnTop = false,
  width = '584px',
  height,
  maxWidth = '100%',
  minWidth,
  className,
  dataTest = 'modal',
  cancelButtonLabel = 'Cancel',
  actionButtonLabel = 'Confirm',
  isActionDisabled = false,
  isActionButtonLoaderShown = false,
  isNeedConfirmationOnCancel = false,
  buttonInControlWithFocus = 'cancel',
  onAction,
  onCancel,
}) => {
  const [isConfirmationDialogOpen, setIsConfirmationDialogOpen] = useState(false);

  // cancel button on Dialog
  const handleCancel = () => {
    if (isNeedConfirmationOnCancel) {
      setIsConfirmationDialogOpen(true);
    } else {
      onCancel();
    }
  };

  // action button on dialog
  const handleAction = () => {
    onAction?.();
  };

  // cancel button on confirm dialog
  const handleDenyCancel = () => {
    setIsConfirmationDialogOpen(false);
  };

  // action button on confirm dialog
  const handleConfirmCancel = () => {
    setIsConfirmationDialogOpen(false);
    onCancel();
  };

  const dialogControlsComponent = dialogControls ?? <DialogDefaultControlsV2 />;

  return (
    <DialogContext.Provider
      value={{
        cancelButtonLabel,
        actionButtonLabel,
        isActionDisabled,
        isActionButtonLoaderShown,
        buttonInControlWithFocus,
        onCancel: handleCancel,
        onAction: handleAction,
      }}
    >
      <Modal
        isOpen={true}
        onOpenChange={handleCancel}
        isDismissDisabled={false}
        className={cn(s.dialog, className)}
        style={{ width, height, maxWidth, minWidth }}
        data-test={dataTest}
      >
        <div className={s.dialogContentWrapper} onClick={(e) => e.stopPropagation()}>
          <IconButton
            icon="g2-close"
            variant="secondary"
            size={24}
            className={s.dialog__close}
            onClick={handleCancel}
            tabIndex={-1}
          />
          {title && (
            <Text variant="h2" className={s.dialog__title}>
              {title}
            </Text>
          )}
          {isDialogControlsOnTop && dialogControlsComponent}
          <div className={s.dialog__body}>{children}</div>
          {!isDialogControlsOnTop && dialogControlsComponent}
        </div>
      </Modal>
      {isConfirmationDialogOpen && (
        <DialogV2
          title="Cancel action"
          isNeedConfirmationOnCancel={false}
          cancelButtonLabel="No"
          actionButtonLabel="Yes"
          onCancel={handleDenyCancel}
          onAction={handleConfirmCancel}
        >
          Are you sure? All changes will not be saved.
        </DialogV2>
      )}
    </DialogContext.Provider>
  );
};

export default DialogV2;
