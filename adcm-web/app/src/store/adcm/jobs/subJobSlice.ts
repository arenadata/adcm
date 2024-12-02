import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { showError } from '@store/notificationsSlice';
import type { AdcmSubJobLogItem, AdcmSubJobDetails } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmJobsApi } from '@api/adcm/jobs';

interface AdcmSubJobState {
  subJob?: AdcmSubJobDetails;
  isLoading: boolean;
  subJobLog: AdcmSubJobLogItem[];
}

const loadSubJobFromBackend = createAsyncThunk('adcm/subJob/loadSubJobFromBackend', async (id: number, thunkAPI) => {
  try {
    const subJob = await AdcmJobsApi.getSubJob(id);
    return subJob;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getSubJob = createAsyncThunk('adcm/subJob/getSubJob', async (id: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI
    .dispatch(loadSubJobFromBackend(id))
    .unwrap()
    .catch(() => {
      thunkAPI.dispatch(showError({ message: 'Subjob not found' }));
    });

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshSubJob = createAsyncThunk('adcm/subJob/refreshSubJob', async (id: number, thunkAPI) => {
  thunkAPI.dispatch(loadSubJobFromBackend(id));
});

const getSubJobLog = createAsyncThunk('adcm/subJob/getSubJobLog', async (id: number, thunkAPI) => {
  try {
    return await AdcmJobsApi.getSubJobLog(id);
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmSubJobState => ({
  subJob: undefined,
  isLoading: true,
  subJobLog: [],
});

const jobsSlice = createSlice({
  name: 'adcm/subJob',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupSubJob() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadSubJobFromBackend.fulfilled, (state, action) => {
        state.subJob = action.payload;
      })
      .addCase(getSubJobLog.fulfilled, (state, action) => {
        state.subJobLog = action.payload;
      });
  },
});

const { setIsLoading, cleanupSubJob } = jobsSlice.actions;
export { getSubJob, refreshSubJob, getSubJobLog, cleanupSubJob };
export default jobsSlice.reducer;
