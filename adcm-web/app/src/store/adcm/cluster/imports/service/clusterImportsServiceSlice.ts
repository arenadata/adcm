import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceImportsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterImport, AdcmClusterImportPostPayload, AdcmError } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError, showSuccess } from '@store/notificationsSlice';
import { LoadState } from '@models/loadState';

type GetClusterImportsArg = {
  clusterId: number;
};

export interface AdcmSaveClusterImportsArgs {
  clusterId: number;
  clusterImportsList: AdcmClusterImportPostPayload[];
}

type AdcmClusterImportsState = {
  clusterImports: AdcmClusterImport[];
  hasSaveError: boolean;
  loadState: LoadState;
  totalCount: number;
};

const loadClusterServiceImports = createAsyncThunk(
  'adcm/cluster/imports/service/loadClusterImports',
  async ({ clusterId }: GetClusterImportsArg, thunkAPI) => {
    const {
      adcm: {
        clusterImportsServiceFilter: {
          paginationParams,
          filter: { serviceId },
        },
      },
    } = thunkAPI.getState();

    if (!serviceId) return;

    try {
      const clusterImports = await AdcmClusterServiceImportsApi.getClusterServiceImports(
        clusterId,
        serviceId,
        paginationParams,
      );
      return clusterImports;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const saveClusterServiceImports = createAsyncThunk(
  'adcm/cluster/imports/service/saveClusterImports',
  async ({ clusterId, clusterImportsList }: AdcmSaveClusterImportsArgs, thunkAPI) => {
    const {
      adcm: {
        clusterImportsServiceFilter: {
          filter: { serviceId },
        },
      },
    } = thunkAPI.getState();

    if (!serviceId) return;

    try {
      await AdcmClusterServiceImportsApi.postClusterServiceImport(clusterId, serviceId, clusterImportsList);
      thunkAPI.dispatch(loadClusterServiceImports({ clusterId }));
      thunkAPI.dispatch(showSuccess({ message: 'Import has been completed' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: (error as RequestError<AdcmError>).response?.data.desc ?? '' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterServiceImports = createAsyncThunk(
  'adcm/cluster/imports/service/getClusterImports',
  async ({ clusterId }: GetClusterImportsArg, thunkAPI) => {
    thunkAPI.dispatch(setLoadState(LoadState.Loading));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterServiceImports({ clusterId }));

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
  loadState: LoadState.Loaded,
  totalCount: 0,
});

const clusterImportsServiceSlice = createSlice({
  name: 'adcm/cluster/imports/service',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServiceImports() {
      return createInitialState();
    },
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServiceImports.fulfilled, (state, action) => {
      if (!action.payload) return;
      state.clusterImports = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClusterServiceImports.rejected, (state) => {
      state.clusterImports = [];
    });
    builder.addCase(saveClusterServiceImports.pending, (state) => {
      state.hasSaveError = false;
    });
    builder.addCase(saveClusterServiceImports.rejected, (state) => {
      state.hasSaveError = true;
    });
  },
});

const { cleanupClusterServiceImports, setLoadState } = clusterImportsServiceSlice.actions;
export { cleanupClusterServiceImports, getClusterServiceImports, saveClusterServiceImports };
export default clusterImportsServiceSlice.reducer;
