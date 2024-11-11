import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { AdcmJob } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmJobsApi } from '@api/adcm/jobs';
import type { PaginationParams, SortParams } from '@models/table';

interface AdcmBellState {
  jobs: AdcmJob[];
  totalCount: number;
  isLoading: boolean;
  filter: object;
  paginationParams: PaginationParams;
  sortParams: SortParams;
  requestFrequency: number;
}

const loadFromBackend = createAsyncThunk('adcm/bell/loadFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      bell: { filter, sortParams, paginationParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmJobsApi.getJobs(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getJobs = createAsyncThunk('adcm/bell/getJobs', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadFromBackend());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshJobs = createAsyncThunk('adcm/jobs/refreshJobs', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend());
});

const createInitialState = (): AdcmBellState => ({
  jobs: [],
  totalCount: 0,
  isLoading: false,
  filter: {},
  paginationParams: { perPage: 5, pageNumber: 0 },
  sortParams: { sortBy: 'id', sortDirection: 'desc' },
  requestFrequency: 5,
});

const bellSlice = createSlice({
  name: 'adcm/bell',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupBell() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadFromBackend.fulfilled, (state, action) => {
        state.jobs = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadFromBackend.rejected, (state) => {
        state.jobs = [];
      });
  },
});

const { setIsLoading, cleanupBell } = bellSlice.actions;
export { cleanupBell, getJobs, refreshJobs };
export default bellSlice.reducer;
