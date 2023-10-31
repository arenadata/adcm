import { EmptyTableFilter, ListState } from '@models/table';
import { createListSlice } from '@store/redux';

type AdcmImportClusterFilterState = ListState<EmptyTableFilter>;
const createInitialState = (): AdcmImportClusterFilterState => ({
  filter: {},
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

const clusterImportFilterSlice = createListSlice({
  name: 'adcm/cluster/imports/clusterFilter',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setSortParams } = clusterImportFilterSlice.actions;
export default clusterImportFilterSlice.reducer;
