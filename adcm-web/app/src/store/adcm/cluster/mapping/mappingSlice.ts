import { PayloadAction, createSlice } from '@reduxjs/toolkit';
import { RequestError, AdcmClusterMappingApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError } from '@store/notificationsSlice';
import { AdcmComponent, AdcmHostShortView, AdcmMapping, AdcmError } from '@models/adcm';

type GetClusterMappingArg = {
  clusterId: number;
};

type SaveClusterMappingArg = {
  clusterId: number;
  mapping: AdcmMapping[];
};

type AdcmClusterMappingsState = {
  mapping: AdcmMapping[];
  localMapping: AdcmMapping[];
  hosts: AdcmHostShortView[];
  components: AdcmComponent[];
  isLoading: boolean;
  isLoaded: boolean;
  hasSaveError: boolean;
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

const createInitialState = (): AdcmClusterMappingsState => ({
  mapping: [],
  localMapping: [],
  hosts: [],
  components: [],
  isLoading: false,
  isLoaded: false,
  hasSaveError: false,
});

const mappingSlice = createSlice({
  name: 'adcm/cluster/mapping',
  initialState: createInitialState(),
  reducers: {
    setLocalMapping(state, action: PayloadAction<AdcmMapping[]>) {
      state.localMapping = action.payload;
    },
    cleanupMappings() {
      return createInitialState();
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
    builder.addCase(saveMapping.fulfilled, (state) => {
      state.hasSaveError = false;
    });
    builder.addCase(saveMapping.rejected, (state) => {
      state.hasSaveError = true;
    });
  },
});

const { setLocalMapping, cleanupMappings } = mappingSlice.actions;
export { getMappings, saveMapping, setLocalMapping, cleanupMappings };
export default mappingSlice.reducer;
