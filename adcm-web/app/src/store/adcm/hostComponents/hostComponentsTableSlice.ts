import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmHostComponentsFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmHostComponentsFilter> => ({
  filter: {
    displayName: undefined,
  },
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

const hostComponentsTableSlice = createListSlice({
  name: 'adcm/hostComponentsTable',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, cleanupList, setSortParams, resetSortParams, setFilter } =
  hostComponentsTableSlice.actions;
export default hostComponentsTableSlice.reducer;
