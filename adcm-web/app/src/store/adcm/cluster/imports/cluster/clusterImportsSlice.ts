import { createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { AdcmClusterImportsApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import type { AdcmClusterImport, AdcmClusterImportPostPayload, AdcmError } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError, showSuccess } from '@store/notificationsSlice';
import { LoadState, RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

type GetClusterImportsArg = {
  clusterId: number;
};

export interface AdcmSaveClusterImportsArgs {
  clusterId: number;
  clusterImportsList: AdcmClusterImportPostPayload[];
}

type AdcmClusterImportsState = {
  clusterImports: AdcmClusterImport[];
  totalCount: number;
  loadState: LoadState;
  hasSaveError: boolean;
  accessCheckStatus: RequestState;
};

const loadClusterImports = createAsyncThunk(
  'adcm/cluster/imports/loadClusterImports',
  async ({ clusterId }: GetClusterImportsArg, thunkAPI) => {
    const {
      adcm: {
        clusterImportsFilter: { paginationParams },
      },
    } = thunkAPI.getState();

    try {
      const clusterImports = await AdcmClusterImportsApi.getClusterImports(clusterId, paginationParams);
      return clusterImports;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const saveClusterImports = createAsyncThunk(
  'adcm/cluster/imports/saveClusterImports',
  async ({ clusterId, clusterImportsList }: AdcmSaveClusterImportsArgs, thunkAPI) => {
    try {
      await AdcmClusterImportsApi.postClusterImport(clusterId, clusterImportsList);
      thunkAPI.dispatch(loadClusterImports({ clusterId }));
      thunkAPI.dispatch(showSuccess({ message: 'Imported objects have been updated' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: (error as RequestError<AdcmError>).response?.data.desc ?? '' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterImports = createAsyncThunk(
  'adcm/cluster/imports/getClusterImports',
  async (arg: GetClusterImportsArg, thunkAPI) => {
    thunkAPI.dispatch(setLoadState(LoadState.Loading));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterImports(arg));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setLoadState(LoadState.Loaded));
      },
    });
  },
);

const createInitialState = (): AdcmClusterImportsState => ({
  clusterImports: [],
  hasSaveError: false,
  loadState: LoadState.NotLoaded,
  totalCount: 0,
  accessCheckStatus: RequestState.NotRequested,
});

const clusterImportsSlice = createSlice({
  name: 'adcm/cluster/imports',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterImports() {
      return createInitialState();
    },
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterImports.fulfilled, (state, action) => {
      state.clusterImports = action.payload.results;
      state.totalCount = action.payload.count;
      state.accessCheckStatus = RequestState.Completed;
    });
    builder.addCase(loadClusterImports.pending, (state) => {
      state.accessCheckStatus = RequestState.Pending;
    });
    builder.addCase(loadClusterImports.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
      state.clusterImports = [];
    });
    builder.addCase(saveClusterImports.pending, (state) => {
      state.hasSaveError = false;
    });
    builder.addCase(saveClusterImports.rejected, (state) => {
      state.hasSaveError = true;
    });
  },
});

const { cleanupClusterImports, setLoadState } = clusterImportsSlice.actions;
export { cleanupClusterImports, getClusterImports, saveClusterImports, setLoadState };
export default clusterImportsSlice.reducer;
