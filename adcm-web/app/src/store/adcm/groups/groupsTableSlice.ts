import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmGroupFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmGroupFilter> => ({
  filter: {
    displayName: undefined,
    type: undefined,
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

const groupsTableSlice = createListSlice({
  name: 'adcm/groupsTable',
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
} = groupsTableSlice.actions;
export default groupsTableSlice.reducer;
