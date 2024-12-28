import type { AdcmAuditOperationFilter } from '@models/adcm';
import { createListSlice } from '@store/redux';
import type { ListState } from '@models/table';
import { getStartDayEndDay } from '@utils/date/calendarUtils';

type AdcmAuditOperationsTableState = ListState<AdcmAuditOperationFilter>;

const createInitialState = (): AdcmAuditOperationsTableState => {
  const [timeFrom, timeTo] = getStartDayEndDay();

  return {
    filter: {
      operationType: undefined,
      operationResult: undefined,
      objectName: undefined,
      objectType: undefined,
      username: undefined,
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

const auditOperationsTableStateSlice = createListSlice({
  name: 'adcm/auditOperationsTable',
  createInitialState,
  reducers: {},
});

export const { setPaginationParams, setSortParams, setRequestFrequency, setFilter, resetFilter, cleanupList } =
  auditOperationsTableStateSlice.actions;
export default auditOperationsTableStateSlice.reducer;
