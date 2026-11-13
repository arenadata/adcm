import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { AdcmJob, AdcmTaskExecutionPlan } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmJobsApi } from '@api/adcm/jobs';
import { showError } from '@store/notificationsSlice';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

interface AdcmJobState {
  job?: AdcmJob;
  executionPlan: AdcmTaskExecutionPlan | null;
  isLoading: boolean;
}

const loadFromBackend = createAsyncThunk('adcm/job/loadFromBackend', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getJob(id);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadExecutionPlanFromBackend = createAsyncThunk(
  'adcm/job/loadExecutionPlanFromBackend',
  async (id: number, thunkAPI) => {
    try {
      return await AdcmJobsApi.getTaskExecutionPlan(id);
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getJob = createAsyncThunk('adcm/job/getJob', async (id: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();
  await Promise.all([
    thunkAPI
      .dispatch(loadFromBackend(id))
      .unwrap()
      .catch(() => {
        thunkAPI.dispatch(showError({ message: 'Job not found' }));
      }),
    thunkAPI.dispatch(loadExecutionPlanFromBackend(id)),
  ]);

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshJob = createAsyncThunk('adcm/job/refreshJob', async (id: number, thunkAPI) => {
  await Promise.all([thunkAPI.dispatch(loadFromBackend(id)), thunkAPI.dispatch(loadExecutionPlanFromBackend(id))]);
});

const createInitialState = (): AdcmJobState => ({
  job: undefined,
  executionPlan: null,
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
    builder.addCase(loadExecutionPlanFromBackend.fulfilled, (state, action) => {
      state.executionPlan = action.payload;
    });
    builder.addCase(loadExecutionPlanFromBackend.rejected, (state) => {
      state.executionPlan = null;
    });
    builder.addCase(wsActions.update_task, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.job?.id === id) {
        state.job = { ...state.job, ...changes };
      }
    });
  },
});

const { setIsLoading, cleanupJob } = jobSlice.actions;
export { getJob, refreshJob, cleanupJob };
export default jobSlice.reducer;
