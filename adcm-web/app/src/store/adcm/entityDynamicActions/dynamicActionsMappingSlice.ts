import { createSlice } from '@reduxjs/toolkit';
import { AdcmHostShortView, AdcmMapping, AdcmMappingComponent, NotAddedServicesDictionary } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterMappingApi } from '@api';
import { LoadState } from '@models/loadState';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { arrayToHash } from '@utils/arrayUtils';

type GetClusterMappingArg = {
  clusterId: number;
};

const loadMappings = createAsyncThunk(
  'adcm/dynamicActionsMapping/loadMappings',
  async ({ clusterId }: GetClusterMappingArg, thunkAPI) => {
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
  'adcm/dynamicActionsMapping/getMappings',
  async (arg: GetClusterMappingArg, thunkAPI) => {
    await thunkAPI.dispatch(loadMappings(arg));
  },
);

type AdcmDynamicActionsState = {
  components: AdcmMappingComponent[];
  mapping: AdcmMapping[];
  hosts: AdcmHostShortView[];
  notAddedServicesDictionary: NotAddedServicesDictionary;
  loadState: LoadState;
};

const createInitialState = (): AdcmDynamicActionsState => ({
  mapping: [],
  hosts: [],
  components: [],
  notAddedServicesDictionary: {},
  loadState: LoadState.NotLoaded,
});

const dynamicActionsMappingSlice = createSlice({
  name: 'adcm/dynamicActionsMapping',
  initialState: createInitialState(),
  reducers: {
    cleanupDynamicActionsMapping() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadMappings.fulfilled, (state, action) => {
      state.mapping = action.payload.mapping;
      state.hosts = action.payload.hosts;
      state.components = action.payload.components;
      state.notAddedServicesDictionary = arrayToHash(action.payload.notAddedServices, (s) => s.id);
    });
    builder.addCase(getMappings.pending, (state) => {
      state.loadState = LoadState.Loading;
    });
    builder.addCase(getMappings.fulfilled, (state) => {
      state.loadState = LoadState.Loaded;
    });
  },
});

export const { cleanupDynamicActionsMapping } = dynamicActionsMappingSlice.actions;
export { getMappings };

export default dynamicActionsMappingSlice.reducer;
