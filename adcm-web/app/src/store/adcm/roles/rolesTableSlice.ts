import { createListSlice } from '@store/redux';
import type { ListState } from '@models/table';
import type { AdcmRolesFilter } from '@models/adcm';
import { AdcmRoleType } from '@models/adcm';

const createInitialState = (): ListState<AdcmRolesFilter> => ({
  filter: {
    displayName: undefined,
    type: AdcmRoleType.Role,
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
