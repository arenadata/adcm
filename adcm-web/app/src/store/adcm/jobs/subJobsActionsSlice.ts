import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getJob } from './jobSlice';
import { AdcmJobsApi } from '@api/adcm/jobs';

export type SubJobTerminateMode = 'skip' | 'stop';

interface AdcmJobsActionState {
  stopDialog: {
    id: number | null;
    mode: SubJobTerminateMode;
    displayName: string | null;
  };
  stopGroupDialog: {
    name: string | null;
    displayName: string | null;
    mode: SubJobTerminateMode;
  };
}

interface StopSubJobWithUpdatePayload {
  subJobId: number;
  jobId: number;
}

interface StopJobGroupWithUpdatePayload {
  jobId: number;
  groupName: string;
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

const stopJobGroup = createAsyncThunk(
  'adcm/subJobsActions/stopJobGroup',
  async ({ jobId, groupName }: StopJobGroupWithUpdatePayload, thunkAPI) => {
    try {
      await AdcmJobsApi.stopJobGroup(jobId, groupName);
      thunkAPI.dispatch(showInfo({ message: 'Group has been stopped' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const stopJobGroupWithUpdate = createAsyncThunk(
  'adcm/subJobsActions/stopJobGroupWithUpdate',
  async (payload: StopJobGroupWithUpdatePayload, thunkAPI) => {
    await thunkAPI.dispatch(stopJobGroup(payload)).unwrap();
    thunkAPI.dispatch(getJob(payload.jobId));
  },
);

const createInitialState = (): AdcmJobsActionState => ({
  stopDialog: {
    id: null,
    mode: 'stop',
    displayName: null,
  },
  stopGroupDialog: {
    name: null,
    displayName: null,
    mode: 'stop',
  },
});

const subJobsSlice = createSlice({
  name: 'adcm/subJobsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openStopDialog(
      state,
      action: PayloadAction<number | { id: number; mode?: SubJobTerminateMode; displayName?: string }>,
    ) {
      if (typeof action.payload === 'number') {
        state.stopDialog.id = action.payload;
        state.stopDialog.mode = 'stop';
        state.stopDialog.displayName = null;
        return;
      }

      state.stopDialog.id = action.payload.id;
      state.stopDialog.mode = action.payload.mode ?? 'stop';
      state.stopDialog.displayName = action.payload.displayName ?? null;
    },
    closeStopDialog(state) {
      state.stopDialog.id = null;
      state.stopDialog.mode = 'stop';
      state.stopDialog.displayName = null;
    },
    openStopGroupDialog(
      state,
      action: PayloadAction<{ name: string; displayName: string; mode?: SubJobTerminateMode }>,
    ) {
      state.stopGroupDialog.name = action.payload.name;
      state.stopGroupDialog.displayName = action.payload.displayName;
      state.stopGroupDialog.mode = action.payload.mode ?? 'stop';
    },
    closeStopGroupDialog(state) {
      state.stopGroupDialog.name = null;
      state.stopGroupDialog.displayName = null;
      state.stopGroupDialog.mode = 'stop';
    },
  },
  extraReducers: (builder) => {
    builder.addCase(stopSubJob.pending, (state) => {
      subJobsSlice.caseReducers.closeStopDialog(state);
    });
    builder.addCase(stopJobGroup.pending, (state) => {
      subJobsSlice.caseReducers.closeStopGroupDialog(state);
    });
  },
});

const { openStopDialog, closeStopDialog, openStopGroupDialog, closeStopGroupDialog } = subJobsSlice.actions;
export {
  stopSubJobWithUpdate,
  stopJobGroupWithUpdate,
  openStopDialog,
  closeStopDialog,
  openStopGroupDialog,
  closeStopGroupDialog,
};
export default subJobsSlice.reducer;
