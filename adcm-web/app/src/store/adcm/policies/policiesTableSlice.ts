import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmPoliciesFilter } from '@models/adcm/policy';

const createInitialState = (): ListState<AdcmPoliciesFilter> => ({
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

const policiesTableSlice = createListSlice({
  name: 'adcm/policiesTable',
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
} = policiesTableSlice.actions;
export default policiesTableSlice.reducer;
