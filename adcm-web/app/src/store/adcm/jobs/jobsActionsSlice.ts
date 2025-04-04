import { createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { refreshJobs } from './jobsSlice';
import { AdcmJobsApi } from '@api/adcm/jobs';

interface AdcmJobsActionState {
  stopDialog: {
    id: number | null;
  };
}

const stopJob = createAsyncThunk('adcm/jobsActions/stopJob', async (id: number, thunkAPI) => {
  try {
    await AdcmJobsApi.stopJob(id);
    thunkAPI.dispatch(showInfo({ message: 'Job has been stopped' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const stopJobWithUpdate = createAsyncThunk('adcm/jobsActions/stopJobWithUpdate', async (arg: number, thunkAPI) => {
  await thunkAPI.dispatch(stopJob(arg)).unwrap();
  thunkAPI.dispatch(refreshJobs());
});

const createInitialState = (): AdcmJobsActionState => ({
  stopDialog: {
    id: null,
  },
});

const jobsSlice = createSlice({
  name: 'adcm/jobsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openStopDialog(state, action) {
      state.stopDialog.id = action.payload;
    },
    closeStopDialog(state) {
      state.stopDialog.id = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(stopJob.pending, (state) => {
      jobsSlice.caseReducers.closeStopDialog(state);
    });
  },
});

const { openStopDialog, closeStopDialog } = jobsSlice.actions;
export { stopJobWithUpdate, openStopDialog, closeStopDialog };
export default jobsSlice.reducer;
