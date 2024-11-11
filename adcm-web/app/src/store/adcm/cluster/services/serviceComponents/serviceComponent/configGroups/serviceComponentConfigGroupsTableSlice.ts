import type { EmptyTableFilter, ListState } from '@models/table';
import { createListSlice } from '@store/redux';

type AdcmServiceComponentConfigGroupsTableState = ListState<EmptyTableFilter>;

const createInitialState = (): AdcmServiceComponentConfigGroupsTableState => ({
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

const serviceComponentConfigGroupsTable = createListSlice({
  name: 'adcm/serviceComponentConfigGroupsTable',
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
} = serviceComponentConfigGroupsTable.actions;
export default serviceComponentConfigGroupsTable.reducer;
