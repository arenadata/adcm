import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmJobsFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmJobsFilter> => ({
  filter: {
    name: undefined,
    object: undefined,
    status: undefined,
  },
  paginationParams: {
    perPage: 10,
    pageNumber: 0,
  },
  requestFrequency: 5,
  sortParams: {
    sortBy: 'id',
    sortDirection: 'desc',
  },
});

const jobsTableSlice = createListSlice({
  name: 'adcm/jobsTable',
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
} = jobsTableSlice.actions;
export default jobsTableSlice.reducer;
