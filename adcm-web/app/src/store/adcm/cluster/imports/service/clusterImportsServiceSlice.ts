import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceImportsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterImport, AdcmClusterImportPostPayload, AdcmError } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError } from '@store/notificationsSlice';

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
  isLoading: boolean;
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
    } catch (error) {
      thunkAPI.dispatch(showError({ message: (error as RequestError<AdcmError>).response?.data.desc ?? '' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterServiceImports = createAsyncThunk(
  'adcm/cluster/imports/service/getClusterImports',
  async ({ clusterId }: GetClusterImportsArg, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterServiceImports({ clusterId }));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const createInitialState = (): AdcmClusterImportsState => ({
  clusterImports: [],
  hasSaveError: false,
  isLoading: false,
  totalCount: 0,
});

const clusterImportsServiceSlice = createSlice({
  name: 'adcm/cluster/imports/service',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServiceImports() {
      return createInitialState();
    },
    setIsLoading(state, action) {
      state.isLoading = action.payload;
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

const { cleanupClusterServiceImports, setIsLoading } = clusterImportsServiceSlice.actions;
export { cleanupClusterServiceImports, getClusterServiceImports, saveClusterServiceImports };
export default clusterImportsServiceSlice.reducer;
