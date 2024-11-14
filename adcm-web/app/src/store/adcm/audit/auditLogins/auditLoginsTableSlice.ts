import type { AdcmAuditLoginFilter } from '@models/adcm';
import { createListSlice } from '@store/redux';
import type { ListState } from '@models/table';
import { getStartDayEndDay } from '@utils/date/calendarUtils';

type AdcmAuditLoginsTableState = ListState<AdcmAuditLoginFilter>;

const createInitialState = (): AdcmAuditLoginsTableState => {
  const [timeFrom, timeTo] = getStartDayEndDay();

  return {
    filter: {
      loginResult: undefined,
      login: undefined,
      timeFrom,
      timeTo,
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
  };
};

const auditLoginsTableStateSlice = createListSlice({
  name: 'adcm/auditLoginsTable',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setSortParams, setRequestFrequency, setFilter, resetFilter, cleanupList } =
  auditLoginsTableStateSlice.actions;
export default auditLoginsTableStateSlice.reducer;
