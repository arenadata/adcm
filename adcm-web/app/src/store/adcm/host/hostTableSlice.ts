import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { AdcmHostComponentsFilter } from '@models/adcm';

const createInitialState = (): ListState<AdcmHostComponentsFilter> => ({
  filter: {
    name: undefined,
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

const hostTableSlice = createListSlice({
  name: 'adcm/host/hostTableSlice',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setRequestFrequency, cleanupList, setSortParams, resetSortParams, setFilter } =
  hostTableSlice.actions;
export default hostTableSlice.reducer;
