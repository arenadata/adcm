import { AdcmClusterHostsApi, AdcmClustersApi, RequestError } from '@api';
import { defaultSpinnerDelay } from '@constants';
import { AdcmClusterHost, AdcmClusterHostComponentsStatus, AdcmServiceComponent } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { createAsyncThunk } from '@store/redux';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';

interface AdcmClusterHostState {
  clusterHost?: AdcmClusterHost;
  isLoading: boolean;
  hostComponentsCounters: {
    successfulHostComponentsCount: number;
    totalHostComponentsCount: number;
  };
  relatedData: {
    hostComponents: AdcmServiceComponent[];
  };
}

interface ClusterHostPayload {
  clusterId: number;
  hostId: number;
}

const loadClusterHost = createAsyncThunk(
  'adcm/cluster/hosts/host/loadClusterHost',
  async ({ clusterId, hostId }: ClusterHostPayload, thunkAPI) => {
    try {
      const host = await AdcmClusterHostsApi.getHost(clusterId, hostId);
      return host;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getClusterHost = createAsyncThunk(
  'adcm/cluster/hosts/host/getClusterHost',
  async (arg: ClusterHostPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    thunkAPI.dispatch(loadClusterHost(arg));
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,

      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const loadRelatedClusterHostComponents = createAsyncThunk(
  'adcm/cluster/hosts/host/loadRelatedClusterHostComponents',
  async ({ clusterId, hostId }: ClusterHostPayload, thunkAPI) => {
    const {
      adcm: {
        clusterHostTable: { paginationParams, filter, sortParams },
      },
    } = thunkAPI.getState();
    try {
      const clusterHostComponents = await AdcmClusterHostsApi.getClusterHostComponents(
        clusterId,
        hostId,
        sortParams,
        paginationParams,
        filter,
      );
      return clusterHostComponents;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getRelatedClusterHostComponents = createAsyncThunk(
  'adcm/cluster/hosts/host/getRelatedClusterHostComponents',
  async (arg: ClusterHostPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    thunkAPI.dispatch(loadRelatedClusterHostComponents(arg));
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,

      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const getClusterHostComponentsStates = createAsyncThunk(
  'adcm/cluster/hosts/host/getClusterHostComponentsStates',
  async ({ clusterId, hostId }: ClusterHostPayload, thunkAPI) => {
    try {
      const states = AdcmClusterHostsApi.getClusterHostComponentsStates(clusterId, hostId);
      return states;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const unlinkClusterHost = createAsyncThunk(
  'adcm/cluster/hosts/host/unlinkClusterHost',
  async ({ clusterId, hostId }: ClusterHostPayload, thunkAPI) => {
    try {
      await AdcmClustersApi.unlinkHost(clusterId, hostId);
      thunkAPI.dispatch(showInfo({ message: 'The host has been unlinked!' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterHostState => ({
  clusterHost: undefined,
  isLoading: false,
  relatedData: {
    hostComponents: [],
  },
  hostComponentsCounters: {
    successfulHostComponentsCount: 0,
    totalHostComponentsCount: 0,
  },
});

const clusterHostSlice = createSlice({
  name: 'adcm/clusters/hosts/clusterHost',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterHost() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterHost.fulfilled, (state, action) => {
      state.clusterHost = action.payload;
    });
    builder.addCase(loadClusterHost.rejected, (state) => {
      state.clusterHost = undefined;
    });
    builder.addCase(loadRelatedClusterHostComponents.fulfilled, (state, action) => {
      state.relatedData.hostComponents = action.payload.results;
    });
    builder.addCase(loadRelatedClusterHostComponents.rejected, (state) => {
      state.relatedData.hostComponents = [];
    });
    builder.addCase(getClusterHostComponentsStates.fulfilled, (state, action) => {
      state.hostComponentsCounters.totalHostComponentsCount = action.payload.hostComponents.length;
      state.hostComponentsCounters.successfulHostComponentsCount = action.payload.hostComponents.filter(
        ({ status }) => status === AdcmClusterHostComponentsStatus.Up,
      ).length;
    });
    builder.addCase(getClusterHostComponentsStates.rejected, (state) => {
      state.hostComponentsCounters.totalHostComponentsCount = 0;
      state.hostComponentsCounters.successfulHostComponentsCount = 0;
    });
  },
});

const { setIsLoading, cleanupClusterHost } = clusterHostSlice.actions;
export {
  getClusterHost,
  cleanupClusterHost,
  getRelatedClusterHostComponents,
  loadRelatedClusterHostComponents,
  getClusterHostComponentsStates,
  unlinkClusterHost,
};
export default clusterHostSlice.reducer;
