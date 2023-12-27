import { PayloadAction, createSlice } from '@reduxjs/toolkit';
import { RequestError, AdcmClusterMappingApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { AdcmMappingComponent, AdcmHostShortView, AdcmMapping, AdcmError, AdcmServicePrototype } from '@models/adcm';
import { ServiceId } from '@pages/cluster/ClusterMapping/ClusterMapping.types';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { arrayToHash } from '@utils/arrayUtils';

type MappingState = 'no-changes' | 'editing' | 'saving';

type GetClusterMappingArg = {
  clusterId: number;
};

type SaveClusterMappingArg = {
  clusterId: number;
  mapping: AdcmMapping[];
};

type AdcmClusterMappingsState = {
  mapping: AdcmMapping[];
  state: MappingState;
  localMapping: AdcmMapping[];
  hosts: AdcmHostShortView[];
  components: AdcmMappingComponent[];
  isLoading: boolean;
  isLoaded: boolean;
  hasSaveError: boolean;
  relatedData: {
    notAddedServicesDictionary: Record<ServiceId, AdcmServicePrototype>;
  };
  requiredServicesDialog: {
    component: AdcmMappingComponent | null;
  };
};

const loadMapping = createAsyncThunk(
  'adcm/cluster/mapping/loadMapping',
  async ({ clusterId }: GetClusterMappingArg, thunkAPI) => {
    try {
      const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
      return mapping;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const saveMapping = createAsyncThunk(
  'adcm/cluster/mapping/saveMapping',
  async ({ clusterId, mapping }: SaveClusterMappingArg, thunkAPI) => {
    try {
      await AdcmClusterMappingApi.postMapping(clusterId, mapping);

      thunkAPI.dispatch(showInfo({ message: 'Mapping was applied successfully' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: (error as RequestError<AdcmError>).response?.data.desc ?? '' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadMappingHosts = createAsyncThunk(
  'adcm/cluster/mapping/loadMappingHosts',
  async ({ clusterId }: GetClusterMappingArg, thunkAPI) => {
    try {
      const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
      return hosts;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadMappingComponents = createAsyncThunk(
  'adcm/cluster/mapping/loadMappingComponents',
  async ({ clusterId }: GetClusterMappingArg, thunkAPI) => {
    try {
      const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
      return components;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getMappings = createAsyncThunk(
  'adcm/cluster/mapping/getMappings',
  async (arg: GetClusterMappingArg, thunkAPI) => {
    const mapping = await thunkAPI.dispatch(loadMapping(arg));
    const hosts = await thunkAPI.dispatch(loadMappingHosts(arg));
    const components = await thunkAPI.dispatch(loadMappingComponents(arg));

    return { mapping, hosts, components };
  },
);

const getNotAddedServices = createAsyncThunk(
  'adcm/cluster/mapping/getNotAddedServices',
  async ({ clusterId }: GetClusterMappingArg, thunkAPI) => {
    try {
      return await AdcmClusterServicesApi.getClusterServiceCandidates(clusterId);
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterMappingsState => ({
  mapping: [],
  state: 'no-changes',
  localMapping: [],
  hosts: [],
  components: [],
  isLoading: false,
  isLoaded: false,
  hasSaveError: false,
  relatedData: {
    notAddedServicesDictionary: {},
  },
  requiredServicesDialog: {
    component: null,
  },
});

const mappingSlice = createSlice({
  name: 'adcm/cluster/mapping',
  initialState: createInitialState(),
  reducers: {
    setLocalMapping(state, action: PayloadAction<AdcmMapping[]>) {
      state.localMapping = action.payload;
      state.state = 'editing';
    },
    revertChanges(state) {
      state.localMapping = state.mapping;
      state.state = 'no-changes';
    },
    cleanupMappings() {
      return createInitialState();
    },
    openRequiredServicesDialog(state, action) {
      state.requiredServicesDialog.component = action.payload;
    },
    closeRequiredServicesDialog(state) {
      state.requiredServicesDialog.component = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getMappings.pending, (state) => {
      state.isLoading = true;
    });
    builder.addCase(getMappings.fulfilled, (state) => {
      state.isLoading = false;
      state.isLoaded = true;
    });
    builder.addCase(getMappings.rejected, (state) => {
      state.isLoading = false;
      state.isLoaded = true;
    });
    builder.addCase(loadMapping.fulfilled, (state, action) => {
      state.mapping = action.payload;
      state.localMapping = action.payload;
    });
    builder.addCase(loadMappingHosts.fulfilled, (state, action) => {
      state.hosts = action.payload;
    });
    builder.addCase(loadMappingComponents.fulfilled, (state, action) => {
      state.components = action.payload;
    });
    builder.addCase(saveMapping.pending, (state) => {
      state.state = 'saving';
    });
    builder.addCase(saveMapping.fulfilled, (state) => {
      state.hasSaveError = false;
      state.state = 'no-changes';
      state.mapping = state.localMapping;
    });
    builder.addCase(saveMapping.rejected, (state) => {
      state.hasSaveError = true;
      state.state = 'editing';
    });
    builder.addCase(getNotAddedServices.fulfilled, (state, action) => {
      state.relatedData.notAddedServicesDictionary = arrayToHash(action.payload, (s) => s.id);
    });
    builder.addCase(getNotAddedServices.rejected, (state) => {
      state.relatedData.notAddedServicesDictionary = {};
    });
  },
});

const { setLocalMapping, revertChanges, cleanupMappings, openRequiredServicesDialog, closeRequiredServicesDialog } =
  mappingSlice.actions;
export {
  getMappings,
  saveMapping,
  setLocalMapping,
  revertChanges,
  cleanupMappings,
  getNotAddedServices,
  openRequiredServicesDialog,
  closeRequiredServicesDialog,
  loadMappingComponents,
};
export default mappingSlice.reducer;
