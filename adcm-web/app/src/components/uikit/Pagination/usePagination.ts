import { useMemo } from 'react';
import type { PaginationDataItem } from '@uikit/Pagination/Pagination.types';

const DECORATION_STEP = 5;

const TRAILING_ITEMS_AMOUNT = 2;

type LinksAt = 'start' | 'center' | 'end' | 'none';

export interface UsePaginationParams {
  /**
   * Current page. Starts with 0
   * */
  pageNumber: number;
  /**
   * Total pages
   * */
  totalItems: number;
  /**
   * Amount of items per page
   * */
  perPage: number;
  /**
   * Max amount of links to show
   * E.g., if `maxItems` === 7
   * 0 1 2 3 4 … 9
   * 0 … 4 5 6 … 9
   * 0 … 5 6 7 8 9
   * */
  maxItems: number;
  /**
   * external flag for override internal hasNext
   */
  isNextBtn?: false | true | null;
}

interface Results {
  hasNext: boolean;
  hasPrev: boolean;
  pageItems: PaginationDataItem[];
  totalPages: number;
}

export function usePagination(params: UsePaginationParams): Results {
  const { pageNumber, totalItems, maxItems, isNextBtn, perPage } = params;
  const totalPages = Math.ceil(totalItems / perPage);
  const hasNext = typeof isNextBtn === 'boolean' ? isNextBtn : pageNumber < totalPages - 1;
  const hasPrev = pageNumber > 0;

  const decorationPrev = pageNumber - DECORATION_STEP >= 0 ? DECORATION_STEP : 0;
  const decorationNext = pageNumber + DECORATION_STEP <= totalPages - 1 ? -DECORATION_STEP : totalPages - 1;

  const linksAt = useMemo<LinksAt>(() => {
    // 0 1 2 3 4
    if (totalPages <= maxItems) {
      return 'none';
    }

    // 0 1 2 3 4 ... 99
    //       ^
    if (pageNumber < maxItems - TRAILING_ITEMS_AMOUNT - 1) {
      return 'start';
    }

    // 0 ... 49 50 60 ... 99
    //          ^
    if (
      pageNumber >= maxItems - TRAILING_ITEMS_AMOUNT - 1 &&
      pageNumber < totalPages - (maxItems - TRAILING_ITEMS_AMOUNT * 2)
    ) {
      return 'center';
    }

    // 0 ... 95 96 97 98 99
    //          ^
    return 'end';
  }, [pageNumber, maxItems, totalPages]);

  const pageItems = useMemo<PaginationDataItem[]>(() => {
    switch (linksAt) {
      case 'none': {
        const from = 0;
        const to = totalPages - 1;
        const index = 0;

        return getLinks(from, to, index);
      }
      case 'start': {
        const from = 0;
        const to = maxItems - TRAILING_ITEMS_AMOUNT - 1;
        const index = 0;
        const startLinks = getLinks(from, to, index);

        return [
          ...startLinks,
          {
            key: startLinks.length.toString(),
            type: 'decoration',
            label: '...',
            pageNumber: decorationNext,
          },
          {
            key: (startLinks.length + 1).toString(),
            type: 'page',
            label: totalPages.toString(),
            pageNumber: totalPages - 1,
          },
        ];
      }
      case 'center': {
        const iterations = maxItems - TRAILING_ITEMS_AMOUNT * 2;
        const spot = Math.ceil(iterations / 2);
        const from = pageNumber - spot + 1;
        const to = from + iterations - 1;
        const index = 2;
        const midLinks = getLinks(from, to, index);

        return [
          {
            key: '0',
            type: 'page',
            label: '1',
            pageNumber: 0,
          },
          {
            key: '1',
            type: 'decoration',
            label: '...',
            pageNumber: decorationPrev,
          },
          ...midLinks,
          {
            key: (index + midLinks.length).toString(),
            type: 'decoration',
            label: '...',
            pageNumber: decorationNext,
          },
          {
            key: (index + midLinks.length + 1).toString(),
            type: 'page',
            label: totalPages.toString(),
            pageNumber: totalPages - 1,
          },
        ];
      }
      case 'end': {
        const from = totalPages - (maxItems - TRAILING_ITEMS_AMOUNT);
        const to = totalPages - 1;
        const index = 2;
        const endLinks = getLinks(from, to, index);

        return [
          {
            key: '0',
            type: 'page',
            label: '1',
            pageNumber: 0,
          },
          {
            key: '1',
            type: 'decoration',
            label: '...',
            pageNumber: decorationPrev,
          },
          ...endLinks,
        ];
      }
      default: {
        return [];
      }
    }
  }, [linksAt, totalPages, maxItems, decorationNext, pageNumber, decorationPrev]);

  return {
    hasNext,
    hasPrev,
    pageItems,
    totalPages,
  };
}

function getLinks(from: number, to: number, index: number): PaginationDataItem[] {
  const links: PaginationDataItem[] = [];
  for (let pageNumber = from; pageNumber <= to; pageNumber += 1) {
    links.push({
      key: (pageNumber - from + index).toString(),
      type: 'page',
      label: (pageNumber + 1).toString(),
      pageNumber,
    });
  }

  return links;
}
