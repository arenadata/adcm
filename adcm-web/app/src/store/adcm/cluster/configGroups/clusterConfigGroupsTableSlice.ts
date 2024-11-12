import type { EmptyTableFilter, ListState } from '@models/table';
import { createListSlice } from '@store/redux';

type AdcmHostsTableState = ListState<EmptyTableFilter>;

const createInitialState = (): AdcmHostsTableState => ({
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

const clusterConfigGroupsTable = createListSlice({
  name: 'adcm/clusterConfigGroupsTable',
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
} = clusterConfigGroupsTable.actions;
export default clusterConfigGroupsTable.reducer;
