import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { AdcmJob } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmJobsApi } from '@api/adcm/jobs';

interface AdcmJobsState {
  jobs: AdcmJob[];
  totalCount: number;
  isLoading: boolean;
}

const loadJobsFromBackend = createAsyncThunk('adcm/jobs/loadJobsFromBackend', async (_arg, thunkAPI) => {
  const {
    adcm: {
      jobsTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmJobsApi.getJobs(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getJobs = createAsyncThunk('adcm/jobs/getJobs', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadJobsFromBackend());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshJobs = createAsyncThunk('adcm/jobs/refreshJobs', async (_arg, thunkAPI) => {
  thunkAPI.dispatch(loadJobsFromBackend());
});

const createInitialState = (): AdcmJobsState => ({
  jobs: [],
  totalCount: 0,
  isLoading: true,
});

const jobsSlice = createSlice({
  name: 'adcm/jobs',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupJobs() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadJobsFromBackend.fulfilled, (state, action) => {
        state.jobs = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadJobsFromBackend.rejected, (state) => {
        state.jobs = [];
      });
  },
});

const { setIsLoading, cleanupJobs } = jobsSlice.actions;
export { getJobs, refreshJobs, cleanupJobs };
export default jobsSlice.reducer;
