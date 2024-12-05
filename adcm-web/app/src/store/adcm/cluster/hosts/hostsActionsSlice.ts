import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmClusterHostsApi, AdcmClustersApi, AdcmHostsApi } from '@api';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmClusterHost, AdcmHost, AddClusterHostsPayload } from '@models/adcm';
import { AdcmMaintenanceMode } from '@models/adcm';
import { getClusterHosts, setHostMaintenanceMode } from './hostsSlice';
import type { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

const loadHosts = createAsyncThunk('adcm/clusterHostsActions/loadHosts', async (_arg, thunkAPI) => {
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

interface AdcmHostsActionsState extends ModalState<AdcmClusterHost, 'clusterHost'> {
  createDialog: {
    isOpen: boolean;
  };
  maintenanceModeDialog: {
    clusterHost: AdcmHost | null;
  };
  unlinkDialog: {
    clusterHost: AdcmHost | null;
  };
  relatedData: {
    hosts: AdcmHost[];
  };
}

const createInitialState = (): AdcmHostsActionsState => ({
  createDialog: {
    isOpen: false,
  },
  updateDialog: {
    clusterHost: null,
  },
  deleteDialog: {
    clusterHost: null,
  },
  maintenanceModeDialog: {
    clusterHost: null,
  },
  unlinkDialog: {
    clusterHost: null,
  },
  relatedData: {
    hosts: [],
  },
});

const clusterHostsActionsSlice = createCrudSlice({
  name: 'adcm/clusterHostsActions',
  entityName: 'clusterHost',
  createInitialState,
  reducers: {
    openUnlinkDialog(state, action) {
      state.unlinkDialog.clusterHost = action.payload;
    },
    closeUnlinkDialog(state) {
      state.unlinkDialog.clusterHost = null;
    },
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.clusterHost = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.clusterHost = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(unlinkHost.pending, (state) => {
      clusterHostsActionsSlice.caseReducers.closeUnlinkDialog(state);
    });
    builder.addCase(addClusterHosts.fulfilled, (state) => {
      clusterHostsActionsSlice.caseReducers.closeCreateDialog(state);
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
  openCreateDialog,
  closeCreateDialog,
  openUnlinkDialog,
  closeUnlinkDialog,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
} = clusterHostsActionsSlice.actions;

export { unlinkHostWithUpdate, loadHosts, addClusterHostsWithUpdate, toggleMaintenanceMode };

export default clusterHostsActionsSlice.reducer;
