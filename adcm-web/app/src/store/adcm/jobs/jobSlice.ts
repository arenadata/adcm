import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { AdcmJob } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmJobsApi } from '@api/adcm/jobs';
import { showError } from '@store/notificationsSlice';

interface AdcmJobState {
  job?: AdcmJob;
  isLoading: boolean;
}

const loadFromBackend = createAsyncThunk('adcm/job/loadFromBackend', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getJob(id);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getJob = createAsyncThunk('adcm/job/getJob', async (id: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();
  await thunkAPI
    .dispatch(loadFromBackend(id))
    .unwrap()
    .catch(() => {
      thunkAPI.dispatch(showError({ message: 'Job not found' }));
    });

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshJob = createAsyncThunk('adcm/job/refreshJob', async (id: number, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend(id));
});

const createInitialState = (): AdcmJobState => ({
  job: undefined,
  isLoading: true,
});

const jobSlice = createSlice({
  name: 'adcm/job',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupJob() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadFromBackend.fulfilled, (state, action) => {
      state.job = action.payload;
    });
  },
});

const { setIsLoading, cleanupJob } = jobSlice.actions;
export { getJob, refreshJob, cleanupJob };
export default jobSlice.reducer;
