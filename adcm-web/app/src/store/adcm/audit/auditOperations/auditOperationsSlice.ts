import { createSlice } from '@reduxjs/toolkit';
import { AdcmAuditOperation } from '@models/adcm/audit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmAuditApi } from '@api/adcm/audit';
import { localDateToServerDate } from '@utils/date/dateConvertUtils';

type AdcmAuditOperationsState = {
  auditOperations: AdcmAuditOperation[];
  totalCount: number;
  isLoading: boolean;
};

const loadAuditOperations = createAsyncThunk('adcm/auditOperations/loadAuditOperations', async (arg, thunkAPI) => {
  const {
    adcm: {
      auditOperationsTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  const prepFilter = {
    ...filter,
    operationTimeAfter: localDateToServerDate(new Date(filter.operationTimeAfter)),
    operationTimeBefore: localDateToServerDate(new Date(filter.operationTimeBefore)),
  };

  try {
    const batch = await AdcmAuditApi.getAuditOperations(prepFilter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getAuditOperations = createAsyncThunk('adcm/auditOperations/getAuditOperations', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadAuditOperations());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshAuditOperations = createAsyncThunk(
  'adcm/auditOperations/refreshAuditOperations',
  async (arg, thunkAPI) => {
    thunkAPI.dispatch(loadAuditOperations());
  },
);

const createInitialState = (): AdcmAuditOperationsState => ({
  auditOperations: [],
  totalCount: 0,
  isLoading: false,
});

const auditOperationsSlice = createSlice({
  name: 'adcm/auditOperations',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupAuditOperations() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadAuditOperations.fulfilled, (state, action) => {
      state.auditOperations = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadAuditOperations.rejected, (state) => {
      state.auditOperations = [];
    });
  },
});

const { setIsLoading, cleanupAuditOperations } = auditOperationsSlice.actions;
export { getAuditOperations, cleanupAuditOperations, refreshAuditOperations };

export default auditOperationsSlice.reducer;
