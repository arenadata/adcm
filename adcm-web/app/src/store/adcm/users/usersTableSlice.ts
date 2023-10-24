import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmUsersFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmUsersFilter> => ({
  filter: {
    username: undefined,
    status: undefined,
    type: undefined,
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

const usersTableSlice = createListSlice({
  name: 'adcm/usersTable',
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
} = usersTableSlice.actions;
export default usersTableSlice.reducer;
