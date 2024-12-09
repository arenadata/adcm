import { createSlice } from '@reduxjs/toolkit';
import type { AdcmAuditLogin } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmAuditApi } from '@api/adcm/audit';
import { localDateToServerDate } from '@utils/date/dateConvertUtils';
import { LoadState } from '@models/loadState';

type AdcmAuditLoginsState = {
  auditLogins: AdcmAuditLogin[];
  totalCount: number;
  loadState: LoadState;
};

const loadAuditLogins = createAsyncThunk('adcm/auditLogins/loadAuditLogins', async (_arg, thunkAPI) => {
  const {
    adcm: {
      auditLoginsTable: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  const prepFilter = {
    ...filter,
    timeFrom: localDateToServerDate(new Date(filter.timeFrom)),
    timeTo: localDateToServerDate(new Date(filter.timeTo)),
  };

  try {
    const batch = await AdcmAuditApi.getAuditLogins(prepFilter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getAuditLogins = createAsyncThunk('adcm/auditLogins/getAuditLogins', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadAuditLogins());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshAuditLogins = createAsyncThunk('adcm/auditLogins/refreshAuditLogins', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadAuditLogins());
});

const createInitialState = (): AdcmAuditLoginsState => ({
  auditLogins: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
});

const auditLoginsSlice = createSlice({
  name: 'adcm/auditLogins',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupAuditLogins() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadAuditLogins.fulfilled, (state, action) => {
      state.auditLogins = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadAuditLogins.rejected, (state) => {
      state.auditLogins = [];
    });
  },
});

const { setLoadState, cleanupAuditLogins } = auditLoginsSlice.actions;
export { getAuditLogins, cleanupAuditLogins, refreshAuditLogins, setLoadState };

export default auditLoginsSlice.reducer;
