import { ListState } from '@models/table';
import { createListSlice } from '@store/redux';
import { AdcmClusterHostsFilter } from '@models/adcm/clusterHosts';

type AdcmClusterHostsTableState = ListState<AdcmClusterHostsFilter>;

const createInitialState = (): AdcmClusterHostsTableState => ({
  filter: {
    name: undefined,
    hostprovider: undefined,
  },
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

const clusterHostsTableSlice = createListSlice({
  name: 'adcm/clusterHostsTable',
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
} = clusterHostsTableSlice.actions;
export default clusterHostsTableSlice.reducer;
