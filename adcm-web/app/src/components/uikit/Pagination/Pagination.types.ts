import React from 'react';
import { SelectOption } from '@uikit/Select/Select.types';
import { PaginationParams } from '@uikit/types/list.types';

export interface PaginationData {
  pageNumber: number;
  perPage: number;
}

export interface PaginationProps {
  pageData: PaginationParams;
  totalItems?: number;
  perPageItems?: SelectOption<number>[];
  onChangeData: (paginationParams: PaginationParams) => void;
  hidePerPage?: boolean;
  frequencyComponent?: React.ReactNode;
  isNextBtn?: false | true | null;
  className?: string;
  dataTest?: string;
}

export interface PaginationDataItem {
  key: string;
  type: 'page' | 'decoration';
  label: string;
  pageNumber: number;
}
