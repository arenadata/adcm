import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmJob, AdcmJobLogItem, AdcmJobStatus, AdcmTask } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmJobsApi } from '@api/adcm/jobs';
import { showError } from '@store/notificationsSlice';

interface AdcmJobsState {
  jobs: AdcmJob[];
  totalCount: number;
  isLoading: boolean;
  job: AdcmJob | null;
  task: AdcmTask;
  jobLogs: Record<number, AdcmJobLogItem[]>;
}

const loadFromBackend = createAsyncThunk('adcm/jobs/loadFromBackend', async (arg, thunkAPI) => {
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

const getJobs = createAsyncThunk('adcm/jobs/getJobs', async (arg, thunkAPI) => {
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

const getJob = createAsyncThunk('adcm/jobs/getJob', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getJob(id);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getJobLog = createAsyncThunk('adcm/jobs/getJobLog', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getJobLog(id);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getTask = createAsyncThunk('adcm/jobs/getTask', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getTask(id);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: 'Task not found' }));
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmJobsState => ({
  jobs: [],
  totalCount: 0,
  isLoading: false,
  job: null,
  task: {
    id: 0,
    name: '',
    displayName: '',
    status: AdcmJobStatus.Created,
    objects: [],
    duration: 0,
    startTime: '',
    endTime: '',
    isTerminatable: false,
    childJobs: [],
  },
  jobLogs: {},
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
      .addCase(loadFromBackend.fulfilled, (state, action) => {
        state.jobs = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadFromBackend.rejected, (state) => {
        state.jobs = [];
      })
      .addCase(getJob.fulfilled, (state, action) => {
        state.job = action.payload;
      })
      .addCase(getJob.rejected, (state) => {
        state.job = null;
      })
      .addCase(getTask.fulfilled, (state, action) => {
        state.task = action.payload;
      })
      .addCase(getTask.rejected, (state) => {
        state.task.childJobs = [];
      })
      .addCase(getJobLog.fulfilled, (state, action) => {
        const taskId = action.meta.arg;
        state.jobLogs[taskId] = action.payload;
      });
  },
});

const { setIsLoading, cleanupJobs } = jobsSlice.actions;
export { cleanupJobs, getJob, getJobs, getJobLog, getTask, refreshJobs };
export default jobsSlice.reducer;
