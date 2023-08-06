import { AdcmAuditOperationFilter } from '@models/adcm';
import { createListSlice } from '@store/redux';
import { ListState } from '@models/table';
import { getStartDayEndDay } from '@utils/date/calendarUtils';

type AdcmAuditOperationsTableState = ListState<AdcmAuditOperationFilter>;

const createInitialState = (): AdcmAuditOperationsTableState => {
  const [operationTimeAfter, operationTimeBefore] = getStartDayEndDay();

  return {
    filter: {
      operationType: undefined,
      operationResult: undefined,
      objectName: undefined,
      objectType: undefined,
      username: undefined,
      operationTimeAfter,
      operationTimeBefore,
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

export const { setPaginationParams, setSortParams, setRequestFrequency, setFilter, resetFilter } =
  auditOperationsTableStateSlice.actions;
export default auditOperationsTableStateSlice.reducer;
