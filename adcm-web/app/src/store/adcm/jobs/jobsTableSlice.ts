import { createListSlice } from '@store/redux';
import type { ListState } from '@models/table';
import type { AdcmJobsFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmJobsFilter> => ({
  filter: {
    jobName: undefined,
    objectName: undefined,
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
