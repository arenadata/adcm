import { createSlice } from '@reduxjs/toolkit';
import { RequestError } from '@api';
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

const stopJobWithUpdate = createAsyncThunk('adcm/jobs/stopJob', async (id: number, thunkAPI) => {
  try {
    await AdcmJobsApi.stopJob(id);
    thunkAPI.dispatch(showInfo({ message: 'Job has been stopped' }));
    await thunkAPI.dispatch(refreshJobs());
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
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
    builder.addCase(stopJobWithUpdate.pending, (state) => {
      jobsSlice.caseReducers.closeStopDialog(state);
    });
  },
});

const { openStopDialog, closeStopDialog } = jobsSlice.actions;
export { stopJobWithUpdate, openStopDialog, closeStopDialog };
export default jobsSlice.reducer;
