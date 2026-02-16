import { createAsyncThunk } from '@store/redux';
import { AdcmClusterMappingApi } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import type { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import { LoadState, RequestState } from '@models/loadState';
import { createSlice } from '@reduxjs/toolkit';
import { arrayToHash } from '@utils/arrayUtils';
import type { AdcmWizardMappingChangeHistory } from '@models/adcm/wizard';

type GetClustersWizardMappingArg = {
  clusterId: number;
};

const loadMappings = createAsyncThunk(
  'adcm/clustersWizardMapping/loadMappings',
  async ({ clusterId }: GetClustersWizardMappingArg, thunkAPI) => {
    try {
      const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
      const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
      const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
      const notAddedServices = await AdcmClusterServicesApi.getClusterServiceCandidates(clusterId);
      return { mapping, components, hosts, notAddedServices };
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getMappings = createAsyncThunk(
  'adcm/clustersWizardMapping/getMappings',
  async (arg: GetClustersWizardMappingArg, thunkAPI) => {
    await thunkAPI.dispatch(loadMappings(arg));
  },
);

const refreshMapping = createAsyncThunk(
  'adcm/clustersWizardMapping/mapping/refreshMapping',
  async ({ clusterId }: GetClustersWizardMappingArg, _thunkAPI) => {
    const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
    return mapping;
  },
);

const refreshMappingHosts = createAsyncThunk(
  'adcm/clustersWizardMapping/mapping/refreshMappingHosts',
  async ({ clusterId }: GetClustersWizardMappingArg, _thunkAPI) => {
    const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
    return hosts;
  },
);

const refreshMappingComponents = createAsyncThunk(
  'adcm/clustersWizardMapping/mapping/refreshMappingComponents',
  async ({ clusterId }: GetClustersWizardMappingArg, _thunkAPI) => {
    const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
    return components;
  },
);

type AdcmClustersWizardState = {
  mapping: {
    mapping: AdcmMapping[];
    hosts: AdcmHostShortView[];
    components: AdcmMappingComponent[];
    loadState: LoadState;
    notAddedServicesDictionary: NotAddedServicesDictionary;
    requiredServicesDialog: {
      component: AdcmMappingComponent | null;
    };
    accessCheckStatus: RequestState;
  };
  hostComponentMapDelta?: AdcmWizardMappingChangeHistory;
  isLoading: boolean;
};

const createInitialState = (): AdcmClustersWizardState => ({
  mapping: {
    mapping: [],
    hosts: [],
    components: [],
    loadState: LoadState.NotLoaded,
    notAddedServicesDictionary: {},
    requiredServicesDialog: {
      component: null,
    },
    accessCheckStatus: RequestState.NotRequested,
  },
  hostComponentMapDelta: undefined,
  isLoading: false,
});

const clustersWizardMappingSlice = createSlice({
  name: 'adcm/clustersWizardMapping',
  initialState: createInitialState(),
  reducers: {
    cleanupClustersWizardMapping() {
      return createInitialState();
    },
    openRequiredServicesDialog(state, action) {
      state.mapping.requiredServicesDialog.component = action.payload;
    },
    closeRequiredServicesDialog(state) {
      state.mapping.requiredServicesDialog.component = null;
    },
    setHostComponentMapDelta(state, action) {
      state.hostComponentMapDelta = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadMappings.fulfilled, (state, action) => {
      state.mapping.mapping = action.payload.mapping;
      state.mapping.hosts = action.payload.hosts;
      state.mapping.components = action.payload.components;
      state.mapping.notAddedServicesDictionary = arrayToHash(action.payload.notAddedServices, (s) => s.id);
    });
    builder.addCase(getMappings.pending, (state) => {
      state.mapping.loadState = LoadState.Loading;
    });
    builder.addCase(getMappings.fulfilled, (state) => {
      state.mapping.loadState = LoadState.Loaded;
    });
    builder.addCase(refreshMapping.fulfilled, (state, action) => {
      state.mapping.mapping = action.payload;
    });
    builder.addCase(refreshMappingHosts.fulfilled, (state, action) => {
      state.mapping.hosts = action.payload;
    });
    builder.addCase(refreshMappingComponents.fulfilled, (state, action) => {
      state.mapping.components = action.payload;
    });
  },
});

export const {
  cleanupClustersWizardMapping,
  openRequiredServicesDialog,
  closeRequiredServicesDialog,
  setHostComponentMapDelta,
} = clustersWizardMappingSlice.actions;
export { getMappings };

export default clustersWizardMappingSlice.reducer;
