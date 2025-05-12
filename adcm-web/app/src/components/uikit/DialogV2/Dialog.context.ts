import { createContextHelper, useContextHelper } from '@hooks/useContextHelper';
import type { Context } from 'react';

interface DialogContextOptions {
  cancelButtonLabel: string;
  actionButtonLabel: string;
  isActionDisabled: boolean;
  isActionButtonLoaderShown: boolean;
  isActionButtonDefaultFocus: boolean;
  onCancel: () => void;
  onAction?: () => void;
}

export const DialogContext = createContextHelper<DialogContextOptions>('DialogContext');

export const useDialogContext = (): DialogContextOptions =>
  useContextHelper<DialogContextOptions>(DialogContext as Context<DialogContextOptions | undefined>);
