import { ListState } from '@models/table';
import { createListSlice } from '@store/redux';
import { AdcmActionHostGroupsFilter } from '@models/adcm';

type AdcmActionHostGroupsTableState = ListState<AdcmActionHostGroupsFilter>;

const createInitialState = (): AdcmActionHostGroupsTableState => ({
  filter: {
    name: undefined,
    hasHost: undefined,
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

const actionHostGroupsTableSlice = createListSlice({
  name: 'adcm/actionHostsGroupsTable',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, cleanupList, setFilter, resetFilter } =
  actionHostGroupsTableSlice.actions;
export default actionHostGroupsTableSlice.reducer;
