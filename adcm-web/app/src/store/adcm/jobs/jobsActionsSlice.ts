import { createSlice } from '@reduxjs/toolkit';
import { RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { refreshJobs } from './jobsSlice';
import { AdcmJobsApi } from '@api/adcm/jobs';

interface AdcmJobsActionState {
  restartDialog: {
    id: number | null;
  };
  stopDialog: {
    id: number | null;
  };
}

const restartJobWithUpdate = createAsyncThunk('adcm/jobs/restartJob', async (id: number, thunkAPI) => {
  try {
    AdcmJobsApi.restartJob(id);
    thunkAPI.dispatch(showInfo({ message: 'Job has been restarted' }));
    await thunkAPI.dispatch(refreshJobs());
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const stopJobWithUpdate = createAsyncThunk('adcm/jobs/stopJob', async (id: number, thunkAPI) => {
  try {
    AdcmJobsApi.stopJob(id);
    thunkAPI.dispatch(showInfo({ message: 'Job has been stopped' }));
    await thunkAPI.dispatch(refreshJobs());
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const createInitialState = (): AdcmJobsActionState => ({
  restartDialog: {
    id: null,
  },
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
    openRestartDialog(state, action) {
      state.restartDialog.id = action.payload;
    },
    closeRestartDialog(state) {
      state.restartDialog.id = null;
    },
    openStopDialog(state, action) {
      state.stopDialog.id = action.payload;
    },
    closeStopDialog(state) {
      state.stopDialog.id = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(restartJobWithUpdate.pending, (state) => {
        jobsSlice.caseReducers.closeRestartDialog(state);
      })
      .addCase(stopJobWithUpdate.pending, (state) => {
        jobsSlice.caseReducers.closeStopDialog(state);
      });
  },
});

const { openRestartDialog, closeRestartDialog, openStopDialog, closeStopDialog } = jobsSlice.actions;
export {
  restartJobWithUpdate,
  stopJobWithUpdate,
  openRestartDialog,
  closeRestartDialog,
  openStopDialog,
  closeStopDialog,
};
export default jobsSlice.reducer;
