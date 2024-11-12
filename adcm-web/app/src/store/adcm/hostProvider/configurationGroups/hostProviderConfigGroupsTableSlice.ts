import type { EmptyTableFilter, ListState } from '@models/table';
import { createListSlice } from '@store/redux';

type AdcmHostProviderTableState = ListState<EmptyTableFilter>;

const createInitialState = (): AdcmHostProviderTableState => ({
  filter: {},
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 0,
  sortParams: {
    sortBy: 'name',
    sortDirection: 'asc',
  },
});

const hostProviderConfigGroupsTable = createListSlice({
  name: 'adcm/hostProviderConfigGroupsTable',
  createInitialState,
  reducers: {},
});

export const {
  setPaginationParams,
  setRequestFrequency,
  cleanupList,
  setFilter,
  resetFilter,
  setSortParams,
  resetSortParams,
} = hostProviderConfigGroupsTable.actions;
export default hostProviderConfigGroupsTable.reducer;
