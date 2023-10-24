import { EmptyTableFilter, ListState } from '@models/table';
import { createListSlice } from '@store/redux';

type AdcmClusterServiceConfigGroupsTableState = ListState<EmptyTableFilter>;

const createInitialState = (): AdcmClusterServiceConfigGroupsTableState => ({
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

const clusterServiceConfigGroupsTable = createListSlice({
  name: 'adcm/clusterServiceConfigGroupsTable',
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
} = clusterServiceConfigGroupsTable.actions;
export default clusterServiceConfigGroupsTable.reducer;
