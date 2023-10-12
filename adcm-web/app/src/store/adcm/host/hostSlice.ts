import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmServiceComponent, AdcmHost, AdcmClusterHostComponentsStatus } from '@models/adcm';
import { AdcmClusterHostsApi, AdcmClustersApi, AdcmHostsApi, RequestError } from '@api';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';

interface AdcmHostState {
  host?: AdcmHost;
  isLoading: boolean;
  relatedData: {
    hostComponents: AdcmServiceComponent[];
  };
  hostComponentsCounters: {
    successfulHostComponentsCount: number;
    totalHostComponentsCount: number;
  };
}

const loadHost = createAsyncThunk('adcm/host/loadHost', async (hostId: number, thunkAPI) => {
  try {
    const host = await AdcmHostsApi.getHost(hostId);
    return host;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const getHost = createAsyncThunk('adcm/host/getHost', async (arg: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadHost(arg));
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,

    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const loadRelatedHostComponents = createAsyncThunk(
  'adcm/host/loadRelatedHostComponents',
  async (hostId: number, thunkAPI) => {
    const {
      adcm: {
        hostTable: { filter, paginationParams, sortParams },
      },
    } = thunkAPI.getState();

    try {
      const relatedHostComponents = await AdcmHostsApi.getRelatedHostComponents(
        hostId,
        sortParams,
        paginationParams,
        filter,
      );
      return relatedHostComponents;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getRelatedHostComponents = createAsyncThunk(
  'adcm/host/getRelatedHostComponents',
  async (arg: number, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    thunkAPI.dispatch(loadRelatedHostComponents(arg));
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,

      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

interface HostPayload {
  clusterId: number;
  hostId: number;
}

const getHostComponentStates = createAsyncThunk(
  'adcm/host/getHostComponentStates',
  async ({ clusterId, hostId }: HostPayload, thunkAPI) => {
    try {
      const hostComponentStates = await AdcmClusterHostsApi.getClusterHostComponentsStates(clusterId, hostId);
      return hostComponentStates;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const unlinkHostWithUpdate = createAsyncThunk(
  'adcm/host/unlinkHostWithUpdate',
  async ({ clusterId, hostId }: HostPayload, thunkAPI) => {
    try {
      await AdcmClustersApi.unlinkHost(clusterId, hostId);
      thunkAPI.dispatch(showInfo({ message: 'The host has been unlinked' }));
      thunkAPI.dispatch(getHost(hostId));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmHostState => ({
  host: undefined,
  isLoading: false,
  relatedData: {
    hostComponents: [],
  },
  hostComponentsCounters: {
    successfulHostComponentsCount: 0,
    totalHostComponentsCount: 0,
  },
});

const hostSlice = createSlice({
  name: 'adcm/hosts',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupHost() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHost.fulfilled, (state, action) => {
      state.host = action.payload;
    });
    builder.addCase(loadHost.rejected, (state) => {
      state.host = undefined;
    });
    builder.addCase(loadRelatedHostComponents.fulfilled, (state, action) => {
      state.relatedData.hostComponents = action.payload.results;
    });
    builder.addCase(loadRelatedHostComponents.rejected, (state) => {
      state.relatedData.hostComponents = [];
    });
    builder.addCase(getHostComponentStates.fulfilled, (state, action) => {
      state.hostComponentsCounters.successfulHostComponentsCount = action.payload.hostComponents.filter(
        (component) => component.status === AdcmClusterHostComponentsStatus.Up,
      ).length;
      state.hostComponentsCounters.totalHostComponentsCount = action.payload.hostComponents.length;
    });
    builder.addCase(getHostComponentStates.rejected, (state) => {
      state.hostComponentsCounters.successfulHostComponentsCount = 0;
      state.hostComponentsCounters.totalHostComponentsCount = 0;
    });
  },
});

const { setIsLoading, cleanupHost } = hostSlice.actions;
export { getHost, cleanupHost, unlinkHostWithUpdate, getRelatedHostComponents, setIsLoading, getHostComponentStates };
export default hostSlice.reducer;
