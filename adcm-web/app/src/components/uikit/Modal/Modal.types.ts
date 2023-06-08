export interface ModalOptions {
  isOpen: boolean;
  onOpenChange: (_isOpen: boolean) => void;
  isDismissDisabled?: boolean;
}
