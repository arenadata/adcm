import React from 'react';
import { SelectOption } from '@uikit/Select/Select.types';

export interface PaginationData {
  pageNumber: number;
  perPage: number | null;
}

export interface PaginationProps {
  pageData: PaginationData;
  totalItems?: number;
  perPageItems?: SelectOption<number>[];
  onChangeData: (paginationData: PaginationData) => void;
  hidePerPage?: boolean;
  frequencyComponent?: React.ReactNode;
  isNextBtn?: false | true | null;
  className?: string;
}

export interface PaginationDataItem {
  key: string;
  type: 'page' | 'decoration';
  label: string;
  pageNumber: number;
}
