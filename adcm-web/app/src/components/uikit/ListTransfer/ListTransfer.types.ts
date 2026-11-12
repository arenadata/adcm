export type ListTransferItem = {
  key: number;
  label: string;
};

export interface ListTransferPanelOptions {
  title: string;
  searchPlaceholder?: string;
  actionButtonLabel?: string;
}

export interface ListTransferItemOptions {
  item: ListTransferItem;
  onReplace: (key: ListTransferItem['key']) => void;
}
