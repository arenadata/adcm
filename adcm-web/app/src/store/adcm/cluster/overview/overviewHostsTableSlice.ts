import type { ListState } from '@models/table';
import { createListSlice } from '@store/redux';
import type { AdcmClusterOverviewHostsFilter } from '@models/adcm';

type AdcmClusterOverviewHostsTableState = ListState<AdcmClusterOverviewHostsFilter>;

const createInitialState = (): AdcmClusterOverviewHostsTableState => ({
  filter: {
    hostsStatus: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 10,
  sortParams: {
    sortBy: '',
    sortDirection: 'asc',
  },
});

const hostsTableSlice = createListSlice({
  name: 'adcm/cluster/overview/hostsTable',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, setFilter, resetFilter, setSortParams, resetSortParams } =
  hostsTableSlice.actions;
export default hostsTableSlice.reducer;
