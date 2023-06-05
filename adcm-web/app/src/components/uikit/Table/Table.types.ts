import React from 'react';

export type AlignType = 'left' | 'center' | 'right';

export interface TableColumn {
  name: string;
  label?: React.ReactNode;
  isSortable?: boolean;
  isCheckAll?: boolean;
  headerAlign?: AlignType;
  width?: string;
  minWidth?: string;
}
export interface TableSelectedAllOptions {
  isAllSelected?: boolean;
  toggleSelectedAll?: (isAllSelected: boolean) => void;
}
