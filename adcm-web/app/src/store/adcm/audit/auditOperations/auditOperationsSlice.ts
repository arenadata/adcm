import { createSlice } from '@reduxjs/toolkit';
import type { AdcmAuditOperation } from '@models/adcm/audit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmAuditApi } from '@api/adcm/audit';
import { localDateToServerDate } from '@utils/date/dateConvertUtils';
import { LoadState } from '@models/loadState';

type AdcmAuditOperationsState = {
  auditOperations: AdcmAuditOperation[];
  totalCount: number;
  loadState: LoadState;
};

const loadAuditOperations = createAsyncThunk('adcm/auditOperations/loadAuditOperations', async (arg, thunkAPI) => {
  const {
    adcm: {
      auditOperationsTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  const prepFilter = {
    ...filter,
    timeFrom: localDateToServerDate(new Date(filter.timeFrom)),
    timeTo: localDateToServerDate(new Date(filter.timeTo)),
  };

  try {
    const batch = await AdcmAuditApi.getAuditOperations(prepFilter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getAuditOperations = createAsyncThunk('adcm/auditOperations/getAuditOperations', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadAuditOperations());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
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
  loadState: LoadState.NotLoaded,
});

const auditOperationsSlice = createSlice({
  name: 'adcm/auditOperations',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
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

const { setLoadState, cleanupAuditOperations } = auditOperationsSlice.actions;
export { getAuditOperations, cleanupAuditOperations, refreshAuditOperations, setLoadState };

export default auditOperationsSlice.reducer;
