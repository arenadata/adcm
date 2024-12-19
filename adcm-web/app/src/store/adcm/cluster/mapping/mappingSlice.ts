import { createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { AdcmClusterMappingApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import type {
  AdcmError,
  AdcmHostShortView,
  AdcmMapping,
  NotAddedServicesDictionary,
  AdcmMappingComponent,
} from '@models/adcm';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { arrayToHash } from '@utils/arrayUtils';
import type { ActionState } from '@models/loadState';
import { RequestState } from '@models/loadState';
import { processErrorResponse } from '@utils/responseUtils';

type GetClusterMappingArg = {
  clusterId: number;
};

type SaveClusterMappingArg = {
  clusterId: number;
  mapping: AdcmMapping[];
};

type AdcmClusterMappingsState = {
  mapping: AdcmMapping[];
  hosts: AdcmHostShortView[];
  components: AdcmMappingComponent[];
  loading: {
    state: ActionState;
  };
  saving: {
    state: ActionState;
  };
  relatedData: {
    notAddedServicesDictionary: NotAddedServicesDictionary;
  };
  requiredServicesDialog: {
    component: AdcmMappingComponent | null;
  };
  accessCheckStatus: RequestState;
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

const refreshMapping = createAsyncThunk(
  'adcm/cluster/mapping/refreshMapping',
  async ({ clusterId }: GetClusterMappingArg, _thunkAPI) => {
    const mapping = await AdcmClusterMappingApi.getMapping(clusterId);
    return mapping;
  },
);

const saveMapping = createAsyncThunk(
  'adcm/cluster/mapping/saveMapping',
  async ({ clusterId, mapping }: SaveClusterMappingArg, thunkAPI) => {
    try {
      await AdcmClusterMappingApi.postMapping(clusterId, mapping);

      thunkAPI.dispatch(showSuccess({ message: 'Mapping was applied successfully' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: (error as RequestError<AdcmError>).response?.data.desc ?? '' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const saveMappingWithUpdate = createAsyncThunk(
  'adcm/cluster/mapping/saveMappingWithUpdate',
  async ({ clusterId, mapping }: SaveClusterMappingArg, thunkAPI) => {
    await thunkAPI.dispatch(saveMapping({ clusterId, mapping })).unwrap();
    await thunkAPI.dispatch(refreshMappings({ clusterId }));
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

const refreshMappingHosts = createAsyncThunk(
  'adcm/cluster/mapping/refreshMappingHosts',
  async ({ clusterId }: GetClusterMappingArg, _thunkAPI) => {
    const hosts = await AdcmClusterMappingApi.getMappingHosts(clusterId);
    return hosts;
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

const refreshMappingComponents = createAsyncThunk(
  'adcm/cluster/mapping/refreshMappingComponents',
  async ({ clusterId }: GetClusterMappingArg, _thunkAPI) => {
    const components = await AdcmClusterMappingApi.getMappingComponents(clusterId);
    return components;
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

const refreshMappings = createAsyncThunk(
  'adcm/cluster/mapping/refreshMappings',
  async (arg: GetClusterMappingArg, thunkAPI) => {
    const mapping = await thunkAPI.dispatch(refreshMapping(arg));
    const hosts = await thunkAPI.dispatch(refreshMappingHosts(arg));
    const components = await thunkAPI.dispatch(refreshMappingComponents(arg));

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
  hosts: [],
  components: [],
  loading: {
    state: 'not-started',
  },
  saving: {
    state: 'not-started',
  },
  relatedData: {
    notAddedServicesDictionary: {},
  },
  requiredServicesDialog: {
    component: null,
  },
  accessCheckStatus: RequestState.NotRequested,
});

const mappingSlice = createSlice({
  name: 'adcm/cluster/mapping',
  initialState: createInitialState(),
  reducers: {
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
      state.loading.state = 'in-progress';
    });
    builder.addCase(getMappings.fulfilled, (state) => {
      state.loading.state = 'completed';
    });
    builder.addCase(getMappings.rejected, (state) => {
      state.loading.state = 'completed';
    });
    builder.addCase(loadMapping.fulfilled, (state, action) => {
      state.mapping = action.payload;
      state.accessCheckStatus = RequestState.Completed;
    });
    builder.addCase(loadMapping.pending, (state) => {
      state.accessCheckStatus = RequestState.Pending;
    });
    builder.addCase(loadMapping.rejected, (state, action) => {
      state.accessCheckStatus = processErrorResponse(action?.payload as RequestError);
    });
    builder.addCase(refreshMapping.fulfilled, (state, action) => {
      state.mapping = action.payload;
    });
    builder.addCase(loadMappingHosts.fulfilled, (state, action) => {
      state.hosts = action.payload;
    });
    builder.addCase(refreshMappingHosts.fulfilled, (state, action) => {
      state.hosts = action.payload;
    });
    builder.addCase(loadMappingComponents.fulfilled, (state, action) => {
      state.components = action.payload;
    });
    builder.addCase(refreshMappingComponents.fulfilled, (state, action) => {
      state.components = action.payload;
    });
    builder.addCase(saveMapping.pending, (state) => {
      state.saving.state = 'in-progress';
    });
    builder.addCase(saveMapping.fulfilled, (state) => {
      state.saving.state = 'completed';
    });
    builder.addCase(saveMapping.rejected, (state) => {
      state.saving.state = 'completed';
    });
    builder.addCase(getNotAddedServices.fulfilled, (state, action) => {
      state.relatedData.notAddedServicesDictionary = arrayToHash(action.payload, (s) => s.id);
    });
    builder.addCase(getNotAddedServices.rejected, (state) => {
      state.relatedData.notAddedServicesDictionary = {};
    });
  },
});

const { cleanupMappings, openRequiredServicesDialog, closeRequiredServicesDialog } = mappingSlice.actions;
export {
  getMappings,
  saveMapping,
  saveMappingWithUpdate,
  cleanupMappings,
  getNotAddedServices,
  openRequiredServicesDialog,
  closeRequiredServicesDialog,
  loadMappingComponents,
};
export default mappingSlice.reducer;
