import type { ListState } from '@models/table';
import { createListSlice } from '@store/redux';
import type { AdcmClusterOverviewServicesFilter } from '@models/adcm';

type AdcmClusterOverviewServicesTableState = ListState<AdcmClusterOverviewServicesFilter>;

const createInitialState = (): AdcmClusterOverviewServicesTableState => ({
  filter: {
    servicesStatus: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 0,
  sortParams: {
    sortBy: '',
    sortDirection: 'asc',
  },
});

const servicesTableSlice = createListSlice({
  name: 'adcm/cluster/overview/servicesTable',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, setFilter, resetFilter, setSortParams, resetSortParams } =
  servicesTableSlice.actions;
export default servicesTableSlice.reducer;
