import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmClusterHostsFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmClusterHostsFilter> => ({
  filter: {
    name: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 5,
  sortParams: {
    sortBy: 'name',
    sortDirection: 'asc',
  },
});

const hostComponentsTableSlice = createListSlice({
  name: 'adcm/cluster/hosts/host/hostComponentsTableSlice',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, cleanupList, setSortParams, resetSortParams, setFilter } =
  hostComponentsTableSlice.actions;
export default hostComponentsTableSlice.reducer;
