import React, { useCallback, useEffect } from 'react';
import PaginationNumButton from './PaginationButtons/PaginationNumButton';
import PaginationStepButton from './PaginationButtons/PaginationStepButton';
import PaginationDots from './PaginationButtons/PaginationDots';
import s from './Pagination.module.scss';
import cn from 'classnames';
import Select from '@uikit/Select/SingleSelect/Select/Select';
import { usePagination } from './usePagination';
import { PaginationDataItem, PaginationProps } from '@uikit/Pagination/Pagination.types';
import { defaultPerPagesList } from '@constants';

const MAX_VISIBLE_ITEMS = 9;
const DEFAULT_PER_PAGE_ITEMS = 14;

interface renderButtonsProps {
  items: PaginationDataItem[];
  setPageNumber: (newPageNumber: number) => void;
  currentPageNumber: number;
}

const RenderNumberButtons = ({ items, setPageNumber, currentPageNumber }: renderButtonsProps) => {
  return (
    <>
      {items.map((item) =>
        item.type === 'page' ? (
          <PaginationNumButton
            key={`numberBtn_${item.key}`}
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
  dataTest = 'pagination',
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

  const setPageNumber = useCallback(
    (newPageNumber: number) => {
      onChangeData({
        perPage,
        pageNumber: newPageNumber,
      });
    },
    [perPage, onChangeData],
  );

  const setPerPage = (newPerPage: number | null) => {
    onChangeData({
      perPage: newPerPage as number,
      pageNumber: 0,
    });
  };

  useEffect(() => {
    if (totalItems > 0 && totalItems <= pageNumber * perPage) {
      setPageNumber(Math.ceil(totalItems / perPage) - 1);
    }
  }, [totalItems, pageNumber, perPage, setPageNumber]);

  return (
    <div className={paginationWrapperClasses} data-test={dataTest}>
      {!hidePerPage && (
        <>
          <span className={s.pagination__selectLabel}>Show</span>
          <Select
            className={s.pagination__select}
            onChange={setPerPage}
            value={pageData.perPage}
            options={perPageItems}
            dataTest="pagination-per-page-popover"
          />
        </>
      )}
      {frequencyComponent && (
        <>
          <span className={s.pagination__selectLabel}>Frequency</span>
          {frequencyComponent}
        </>
      )}
      <div className={s.pagination__buttonWrapper} data-test="pagination-button-container">
        <RenderNumberButtons setPageNumber={setPageNumber} items={pageItems} currentPageNumber={pageNumber} />
        {totalPages === 0 && (
          <PaginationStepButton arrowVariant={'arrowDouble'} onClick={() => setPageNumber(0)} disabled={!hasPrev} />
        )}
        <PaginationStepButton
          arrowVariant={'arrowSingle'}
          onClick={() => setPageNumber(pageNumber - 1)}
          disabled={!hasPrev}
          dataTest="pagination-prev-page"
        />
        <PaginationStepButton
          arrowVariant={'arrowSingle'}
          onClick={() => setPageNumber(pageNumber + 1)}
          variant={'next'}
          disabled={!hasNext}
          dataTest="pagination-next-page"
        />
      </div>
    </div>
  );
};

export default Pagination;
