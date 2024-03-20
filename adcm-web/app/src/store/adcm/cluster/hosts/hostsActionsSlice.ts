import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterHostsApi, AdcmClustersApi, AdcmHostsApi, RequestError } from '@api';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmHost, AdcmMaintenanceMode, AddClusterHostsPayload } from '@models/adcm';
import { getClusterHosts, setHostMaintenanceMode } from './hostsSlice';

const loadHosts = createAsyncThunk('adcm/clusterHostsActions/loadHosts', async (arg, thunkAPI) => {
  try {
    const hostsDefault = await AdcmHostsApi.getHosts();

    const hosts = await AdcmHostsApi.getHosts(
      {},
      { sortBy: 'name', sortDirection: 'asc' },
      { pageNumber: 0, perPage: hostsDefault.count },
    );
    return hosts.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

interface UnlinkHostTogglePayload {
  hostId: number;
  clusterId: number;
}

interface toggleMaintenanceModePayload {
  hostId: number;
  clusterId: number;
  maintenanceMode: AdcmMaintenanceMode;
}

const unlinkHost = createAsyncThunk(
  'adcm/clusterHostsActions/unlinkHost',
  async ({ hostId, clusterId }: UnlinkHostTogglePayload, thunkAPI) => {
    try {
      await AdcmClustersApi.unlinkHost(clusterId, hostId);
      thunkAPI.dispatch(showSuccess({ message: 'The host has been unlinked' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const unlinkHostWithUpdate = createAsyncThunk(
  'adcm/clusterHostsActions/unlinkHostWithUpdate',
  async (arg: UnlinkHostTogglePayload, thunkAPI) => {
    await thunkAPI.dispatch(unlinkHost(arg)).unwrap();
    thunkAPI.dispatch(getClusterHosts(arg.clusterId));
  },
);

const addClusterHosts = createAsyncThunk(
  'adcm/clusterHostsActions/addClusterHosts',
  async ({ clusterId, selectedHostIds }: AddClusterHostsPayload, thunkAPI) => {
    try {
      await AdcmClustersApi.linkHost(clusterId, selectedHostIds);

      const message = selectedHostIds.length > 1 ? 'All selected hosts have been added' : 'The host has been added';
      thunkAPI.dispatch(showSuccess({ message }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const addClusterHostsWithUpdate = createAsyncThunk(
  'adcm/clusterHostsActions/addClusterHosts',
  async (arg: AddClusterHostsPayload, thunkAPI) => {
    await thunkAPI.dispatch(addClusterHosts(arg)).unwrap();
    thunkAPI.dispatch(getClusterHosts(arg.clusterId));
  },
);

const toggleMaintenanceMode = createAsyncThunk(
  'adcm/clusterHostsActions/toggleMaintenanceMode',
  async ({ clusterId, hostId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      const data = await AdcmClusterHostsApi.toggleMaintenanceMode(clusterId, hostId, maintenanceMode);
      const maintenanceModeStatus = maintenanceMode === AdcmMaintenanceMode.Off ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
      thunkAPI.dispatch(setHostMaintenanceMode({ hostId, maintenanceMode }));
      return data;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmHostsActionsState {
  addDialog: {
    isOpen: boolean;
  };
  maintenanceModeDialog: {
    isOpen: boolean;
    host: AdcmHost | null;
  };
  unlinkDialog: {
    id: null;
  };
  relatedData: {
    hosts: AdcmHost[];
  };
}

const createInitialState = (): AdcmHostsActionsState => ({
  addDialog: {
    isOpen: false,
  },
  maintenanceModeDialog: {
    isOpen: false,
    host: null,
  },
  unlinkDialog: {
    id: null,
  },
  relatedData: {
    hosts: [],
  },
});

const clusterHostsActionsSlice = createSlice({
  name: 'adcm/clusterHostsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openUnlinkDialog(state, action) {
      state.unlinkDialog.id = action.payload;
    },
    closeUnlinkDialog(state) {
      state.unlinkDialog.id = null;
    },
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.isOpen = true;
      state.maintenanceModeDialog.host = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.isOpen = false;
      state.maintenanceModeDialog.host = null;
    },
    openAddDialog(state) {
      state.addDialog.isOpen = true;
    },
    closeAddDialog(state) {
      state.addDialog.isOpen = false;
      state.relatedData.hosts = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(unlinkHost.pending, (state) => {
      clusterHostsActionsSlice.caseReducers.closeUnlinkDialog(state);
    });
    builder.addCase(addClusterHosts.fulfilled, (state) => {
      clusterHostsActionsSlice.caseReducers.closeAddDialog(state);
    });
    builder.addCase(getClusterHosts.pending, () => {
      // hide actions dialogs, when load new hosts list (not silent refresh)
      clusterHostsActionsSlice.caseReducers.cleanupActions();
    });
    builder.addCase(loadHosts.fulfilled, (state, action) => {
      state.relatedData.hosts = action.payload;
    });
    builder.addCase(loadHosts.rejected, (state) => {
      state.relatedData.hosts = [];
    });
    builder.addCase(toggleMaintenanceMode.pending, (state) => {
      clusterHostsActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
  },
});

export const {
  openAddDialog,
  closeAddDialog,
  openUnlinkDialog,
  closeUnlinkDialog,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
} = clusterHostsActionsSlice.actions;

export { unlinkHostWithUpdate, loadHosts, addClusterHostsWithUpdate, toggleMaintenanceMode };

export default clusterHostsActionsSlice.reducer;
