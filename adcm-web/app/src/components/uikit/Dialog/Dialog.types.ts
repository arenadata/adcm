export interface DialogControlsOptions {
  cancelButtonLabel?: string;
  actionButtonLabel?: string;
  onCancel?: () => void;
  onAction?: () => void;
  isActionDisabled?: boolean;
}
