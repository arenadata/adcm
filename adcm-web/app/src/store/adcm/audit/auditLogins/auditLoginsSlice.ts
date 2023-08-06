import { createSlice } from '@reduxjs/toolkit';
import { AdcmAuditLogin } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmAuditApi } from '@api/adcm/audit';
import { localDateToServerDate } from '@utils/date/dateConvertUtils';

type AdcmAuditLoginsState = {
  auditLogins: AdcmAuditLogin[];
  totalCount: number;
  isLoading: boolean;
};

const loadAuditLogins = createAsyncThunk('adcm/auditLogins/loadAuditLogins', async (arg, thunkAPI) => {
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

const getAuditLogins = createAsyncThunk('adcm/auditLogins/getAuditLogins', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadAuditLogins());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshAuditLogins = createAsyncThunk('adcm/auditLogins/refreshAuditLogins', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadAuditLogins());
});

const createInitialState = (): AdcmAuditLoginsState => ({
  auditLogins: [],
  totalCount: 0,
  isLoading: false,
});

const auditLoginsSlice = createSlice({
  name: 'adcm/auditLogins',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
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

const { setIsLoading, cleanupAuditLogins } = auditLoginsSlice.actions;
export { getAuditLogins, cleanupAuditLogins, refreshAuditLogins };

export default auditLoginsSlice.reducer;
