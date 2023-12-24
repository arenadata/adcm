export interface ModalOptions {
  isOpen: boolean;
  onOpenChange: (isOpen: boolean) => void;
  isDismissDisabled?: boolean;
}
