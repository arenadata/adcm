import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmObjectCandidates, AdcmPolicy } from '@models/adcm/policy';
import type { RequestError } from '@api';
import { AdcmClustersApi, AdcmHostProvidersApi, AdcmHostsApi, AdcmPoliciesApi } from '@api';
import type { SortParams } from '@models/table';
import type { AdcmCluster, AdcmHost, AdcmHostProvider, AdcmService } from '@models/adcm';
import { LoadState } from '@models/loadState';

interface AdcmPoliciesState {
  policies: AdcmPolicy[];
  totalCount: number;
  loadState: LoadState;
  relatedData: {
    clusters: AdcmCluster[];
    services: AdcmService[];
    hosts: AdcmHost[];
    hostproviders: AdcmHostProvider[];
    objectTypes: string[];
    objectCandidates: AdcmObjectCandidates;
  };
}

const loadPoliciesFromBackend = createAsyncThunk('adcm/policies/loadPoliciesFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      policiesTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmPoliciesApi.getPolicies(filter, paginationParams, sortParams);
    return batch;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const getPolicies = createAsyncThunk('adcm/policies/getPolicies', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadPoliciesFromBackend());

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const refreshPolicies = createAsyncThunk('adcm/policies/refreshPolicies', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadPoliciesFromBackend());
});

const getObjectCandidates = createAsyncThunk('adcm/policies/getObjectCandidates', async (roleId: number, thunkAPI) => {
  thunkAPI.dispatch(setLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadObjectCandidates(roleId));

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLoadState(LoadState.Loaded));
    },
  });
});

const loadObjectCandidates = createAsyncThunk(
  'adcm/policies/loadObjectCandidates',
  async (roleId: number, thunkAPI) => {
    try {
      const objectCandidates = await AdcmPoliciesApi.loadObjectCandidates(roleId);
      return objectCandidates;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const loadClusters = createAsyncThunk('adcm/policies/loadClusters', async (arg, thunkAPI) => {
  try {
    const clusters = await AdcmClustersApi.getClusters();
    return clusters.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadHosts = createAsyncThunk('adcm/policies/loadHosts', async (arg, thunkAPI) => {
  try {
    const hosts = await AdcmHostsApi.getHosts();
    return hosts.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadHostProviders = createAsyncThunk('adcm/policies/loadHostProviders', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultSortParams: SortParams = { sortBy: 'name', sortDirection: 'asc' };

    const hostProviders = await AdcmHostProvidersApi.getHostProviders(emptyFilter, defaultSortParams);
    return hostProviders.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createInitialState = (): AdcmPoliciesState => ({
  policies: [],
  totalCount: 0,
  loadState: LoadState.NotLoaded,
  relatedData: {
    clusters: [],
    services: [],
    hosts: [],
    hostproviders: [],
    objectTypes: [],
    objectCandidates: {
      cluster: [],
      provider: [],
      service: [],
      host: [],
    },
  },
});

const policiesSlice = createSlice({
  name: 'adcm/policies',
  initialState: createInitialState(),
  reducers: {
    setLoadState(state, action) {
      state.loadState = action.payload;
    },
    cleanupPolicies: () => {
      return createInitialState();
    },
  },
  extraReducers(builder) {
    builder.addCase(loadPoliciesFromBackend.fulfilled, (state, action) => {
      state.policies = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadPoliciesFromBackend.rejected, (state) => {
      state.policies = [];
    });
    builder.addCase(loadObjectCandidates.fulfilled, (state, action) => {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.relatedData.objectCandidates = action.payload;
    });
    builder.addCase(loadObjectCandidates.rejected, (state) => {
      state.relatedData.objectCandidates = {
        cluster: [],
        provider: [],
        service: [],
        host: [],
      };
    });
    builder.addCase(loadClusters.fulfilled, (state, action) => {
      state.relatedData.clusters = action.payload;
    });
    builder.addCase(loadClusters.rejected, (state) => {
      state.relatedData.clusters = [];
    });
    builder.addCase(loadHosts.fulfilled, (state, action) => {
      state.relatedData.hosts = action.payload;
    });
    builder.addCase(loadHosts.rejected, (state) => {
      state.relatedData.hosts = [];
    });
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.relatedData.hostproviders = action.payload;
    });
    builder.addCase(loadHostProviders.rejected, (state) => {
      state.relatedData.hostproviders = [];
    });
  },
});

const { setLoadState, cleanupPolicies } = policiesSlice.actions;
export {
  getPolicies,
  refreshPolicies,
  getObjectCandidates,
  loadClusters,
  loadHosts,
  loadHostProviders,
  cleanupPolicies,
};
export default policiesSlice.reducer;
