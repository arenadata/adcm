import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmRolesFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmRolesFilter> => ({
  filter: {
    name: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 5,
  sortParams: {
    sortBy: '',
    sortDirection: 'asc',
  },
});

const rolesTableSlice = createListSlice({
  name: 'adcm/rolesTable',
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
} = rolesTableSlice.actions;
export default rolesTableSlice.reducer;
