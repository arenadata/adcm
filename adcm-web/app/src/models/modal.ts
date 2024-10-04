type ModalStateActionData<T, EntityName extends string> = {
  [P in EntityName]: T | unknown;
} & {
  [key: string]: unknown;
};

export interface ModalState<T, EntityName extends string> {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: ModalStateActionData<T, EntityName>;
  deleteDialog: ModalStateActionData<T, EntityName>;
  isActionInProgress?: boolean;
}
