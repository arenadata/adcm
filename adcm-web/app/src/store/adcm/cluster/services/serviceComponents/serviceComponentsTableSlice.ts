import { createListSlice } from '@store/redux';
import type { EmptyTableFilter, ListState } from '@models/table';

type AdcmServiceComponentsFilterState = ListState<EmptyTableFilter>;

const createInitialState = (): AdcmServiceComponentsFilterState => ({
  filter: {},
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 0,
  sortParams: {
    sortBy: 'displayName',
    sortDirection: 'asc',
  },
});

const serviceComponentsTableSlice = createListSlice({
  name: 'adcm/cluster/services/serviceComponentsTableSlice',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, cleanupList, setSortParams, resetSortParams } =
  serviceComponentsTableSlice.actions;
export default serviceComponentsTableSlice.reducer;
