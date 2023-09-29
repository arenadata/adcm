export type ListTransferItem = {
  key: number;
  label: string;
  isInclude?: boolean;
};

export interface ListTransferPanelOptions {
  title: string;
  searchPlaceholder?: string;
  actionButtonLabel?: string;
}

export interface ListTransferItemOptions {
  item: ListTransferItem;
  onReplace: (key: ListTransferItem['key']) => void;
  onSelect: (key: ListTransferItem['key'], isSelected: boolean) => void;
  isSelected?: boolean;
}
