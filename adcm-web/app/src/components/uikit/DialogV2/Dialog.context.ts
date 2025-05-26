import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';
import type { Context } from 'react';
import type { ButtonsInControl } from '@uikit/DialogV2/Dialog';

interface DialogContextOptions {
  cancelButtonLabel: string;
  actionButtonLabel: string;
  isActionDisabled: boolean;
  isActionButtonLoaderShown: boolean;
  buttonInControlWithFocus: ButtonsInControl;
  onCancel: () => void;
  onAction?: () => void;
}

export const DialogContext = createContextHelper<DialogContextOptions>('DialogContext');

export const useDialogContext = (): DialogContextOptions =>
  useContextHelper<DialogContextOptions>(DialogContext as Context<DialogContextOptions | undefined>);
