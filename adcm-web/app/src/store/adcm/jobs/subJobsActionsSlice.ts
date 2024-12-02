import { createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getJob } from './jobSlice';
import { AdcmJobsApi } from '@api/adcm/jobs';

interface AdcmJobsActionState {
  stopDialog: {
    id: number | null;
  };
}

interface StopSubJobWithUpdatePayload {
  subJobId: number;
  jobId: number;
}

const stopSubJob = createAsyncThunk('adcm/subJobsActions/stopSubJob', async (subJobId: number, thunkAPI) => {
  try {
    await AdcmJobsApi.stopSubJob(subJobId);
    thunkAPI.dispatch(showInfo({ message: 'Subjob has been stopped' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const stopSubJobWithUpdate = createAsyncThunk(
  'adcm/subJobsActions/stopSubJobWithUpdate',
  async ({ subJobId, jobId }: StopSubJobWithUpdatePayload, thunkAPI) => {
    await thunkAPI.dispatch(stopSubJob(subJobId)).unwrap();
    thunkAPI.dispatch(getJob(jobId));
  },
);

const createInitialState = (): AdcmJobsActionState => ({
  stopDialog: {
    id: null,
  },
});

const subJobsSlice = createSlice({
  name: 'adcm/subJobsActions',
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
    builder.addCase(stopSubJob.pending, (state) => {
      subJobsSlice.caseReducers.closeStopDialog(state);
    });
  },
});

const { openStopDialog, closeStopDialog } = subJobsSlice.actions;
export { stopSubJobWithUpdate, openStopDialog, closeStopDialog };
export default subJobsSlice.reducer;
