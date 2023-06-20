import React from 'react';
import PaginationNumButton from './SubComponents/PaginationButtons/PaginationNumButton';
import PaginationStepButton from './SubComponents/PaginationButtons/PaginationStepButton';
import PaginationDots from './SubComponents/PaginationButtons/PaginationDots';
import s from './Pagination.module.scss';
import cn from 'classnames';
import Select from '@uikit/Select/SingleSelect/Select/Select';
import { SelectOption } from '@uikit/Select/Select.types';
import { usePagination, PaginationDataItem } from '@uikit/hooks/usePagination';

const MAX_VISIBLE_ITEMS = 9;
const DEFAULT_PER_PAGE_ITEMS = 14;

export interface PaginationDataProps {
  pageNumber: number;
  perPage: number | null;
}

export interface PaginationProps {
  pageData: PaginationDataProps;
  totalItems?: number;
  perPageItems?: SelectOption<number>[];
  onChangeData: (_paginationData: PaginationDataProps) => void;
  hidePerPage?: boolean;
  frequencyComponent?: React.ReactNode;
  isNextBtn?: false | true | null;
  className?: string;
}

interface renderButtonsProps {
  items: PaginationDataItem[];
  setPageNumber: (_newPageNumber: number) => void;
  currentPageNumber: number;
}

export const defaultPerPagesList: SelectOption<number>[] = [
  { value: 10, label: '10 per page' },
  { value: 30, label: '30 per page' },
  { value: 50, label: '50 per page' },
  { value: 100, label: '100 per page' },
];

const RenderNumberButtons = ({ items, setPageNumber, currentPageNumber }: renderButtonsProps) => {
  return (
    <>
      {items.map((item) =>
        item.type === 'page' ? (
          <PaginationNumButton
            key={`numberBtn_${item.key}`}
            btnType="number"
            onClick={() => setPageNumber(item.pageNumber)}
            selected={currentPageNumber === item.pageNumber}
          >
            {item.label}
          </PaginationNumButton>
        ) : (
          <PaginationDots
            key={`dots_${item.key}`}
            dotsHandler={() => setPageNumber(currentPageNumber - item.pageNumber)}
          >
            {item.label}
          </PaginationDots>
        ),
      )}
    </>
  );
};

const Pagination = ({
  pageData,
  totalItems = 0,
  onChangeData,
  hidePerPage = false,
  perPageItems = defaultPerPagesList,
  frequencyComponent,
  isNextBtn = null,
  className = '',
}: PaginationProps) => {
  const { pageNumber, perPage } = pageData;
  const { hasNext, hasPrev, pageItems, totalPages } = usePagination({
    pageNumber,
    perPage: perPage || DEFAULT_PER_PAGE_ITEMS,
    totalItems: totalItems || 0,
    maxItems: MAX_VISIBLE_ITEMS,
    isNextBtn,
  });
  const paginationWrapperClasses = cn(s.paginationWrapper, className || '');

  const setPageNumber = (newPageNumber: number) => {
    onChangeData({
      perPage,
      pageNumber: newPageNumber,
    });
  };

  const setPerPage = (newPerPage: number | null) => {
    onChangeData({
      perPage: newPerPage,
      pageNumber: 0,
    });
  };

  return (
    <div className={paginationWrapperClasses}>
      {!hidePerPage && (
        <>
          <span className={s.pagination__selectLabel}>Show</span>
          <Select
            className={s.pagination__select}
            onChange={setPerPage}
            value={pageData.perPage}
            options={perPageItems}
          />
        </>
      )}
      {frequencyComponent && (
        <>
          <span className={s.pagination__selectLabel}>Frequency</span>
          {frequencyComponent}
        </>
      )}
      <div className={s.pagination__buttonWrapper}>
        <RenderNumberButtons setPageNumber={setPageNumber} items={pageItems} currentPageNumber={pageNumber} />
        {totalPages === 0 && (
          <PaginationStepButton arrowVariant={'arrowDouble'} onClick={() => setPageNumber(0)} disabled={!hasPrev} />
        )}
        <PaginationStepButton
          arrowVariant={'arrowSingle'}
          onClick={() => setPageNumber(pageNumber - 1)}
          disabled={!hasPrev}
        />
        <PaginationStepButton
          arrowVariant={'arrowSingle'}
          onClick={() => setPageNumber(pageNumber + 1)}
          variant={'next'}
          disabled={!hasNext}
        />
      </div>
    </div>
  );
};

export default Pagination;
