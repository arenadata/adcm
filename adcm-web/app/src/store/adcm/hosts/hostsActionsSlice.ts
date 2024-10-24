import { createAsyncThunk } from '@store/redux';
import { getHosts, setHostMaintenanceMode } from '@store/adcm/hosts/hostsSlice';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmClustersApi, AdcmHostProvidersApi, AdcmHostsApi, RequestError } from '@api';
import {
  AdcmCluster,
  AdcmHost,
  AdcmHostProvider,
  AdcmMaintenanceMode,
  AdcmRenameArgs,
  CreateAdcmHostPayload,
} from '@models/adcm';
import { SortParams } from '@models/table';
import { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

const loadClusters = createAsyncThunk('adcm/hostsActions/loadClusters', async (arg, thunkAPI) => {
  try {
    const clusters = await AdcmClustersApi.getClusters();
    return clusters.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadHostProviders = createAsyncThunk('adcm/hostsActions/hostProviders', async (arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultSortParams: SortParams = { sortBy: 'name', sortDirection: 'asc' };

    const hostProviders = await AdcmHostProvidersApi.getHostProviders(emptyFilter, defaultSortParams);
    return hostProviders.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

interface LinkHostTogglePayload {
  hostId: number[];
  clusterId: number;
}

interface UnlinkHostTogglePayload {
  hostId: number;
  clusterId: number;
}

const unlinkHost = createAsyncThunk(
  'adcm/hostsActions/unlinkHost',
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
  'adcm/hostsActions/unlinkHostWithUpdate',
  async (arg: UnlinkHostTogglePayload, thunkAPI) => {
    await thunkAPI.dispatch(unlinkHost(arg)).unwrap();
    thunkAPI.dispatch(getHosts());
  },
);

const linkHost = createAsyncThunk(
  'adcm/hostsActions/linkHost',
  async ({ hostId, clusterId }: LinkHostTogglePayload, thunkAPI) => {
    try {
      await AdcmClustersApi.linkHost(clusterId, hostId);
      thunkAPI.dispatch(showSuccess({ message: 'The host has been linked' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const linkHostWithUpdate = createAsyncThunk(
  'adcm/hostsActions/linkHostWithUpdate',
  async (arg: LinkHostTogglePayload, thunkAPI) => {
    await thunkAPI.dispatch(linkHost(arg)).unwrap();
    thunkAPI.dispatch(getHosts());
  },
);

const createHost = createAsyncThunk(
  'adcm/hostsActions/createHost',
  async (payload: CreateAdcmHostPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsActionInProgress(true));
      const host = await AdcmHostsApi.createHost(payload);
      return host;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsActionInProgress(false));
    }
  },
);

const createHostWithUpdate = createAsyncThunk(
  'adcm/hostsActions/createHostWithUpdate',
  async (payload: CreateAdcmHostPayload, thunkAPI) => {
    await thunkAPI.dispatch(createHost(payload)).unwrap();
    await thunkAPI.dispatch(getHosts());
  },
);

interface toggleMaintenanceModePayload {
  hostId: number;
  maintenanceMode: AdcmMaintenanceMode;
}

const toggleMaintenanceMode = createAsyncThunk(
  'adcm/hostsActions/toggleMaintenanceMode',
  async ({ hostId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      const data = await AdcmHostsApi.toggleMaintenanceMode(hostId, maintenanceMode);
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

const deleteHost = createAsyncThunk('adcm/hostsActions/deleteHost', async (hostId: number, thunkAPI) => {
  try {
    await AdcmHostsApi.deleteHost(hostId);
    thunkAPI.dispatch(showSuccess({ message: 'The host has been deleted' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const deleteHostWithUpdate = createAsyncThunk(
  'adcm/hostsActions/deleteHostWithUpdate',
  async (arg: number, thunkAPI) => {
    await thunkAPI.dispatch(deleteHost(arg)).unwrap();
    thunkAPI.dispatch(getHosts());
  },
);

const updateHost = createAsyncThunk('adcm/hostsActions/updateHost', async ({ id, name }: AdcmRenameArgs, thunkAPI) => {
  try {
    return await AdcmHostsApi.patchHost(id, { name });
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

interface AdcmHostsActionsState extends ModalState<AdcmHost, 'host'> {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    host: AdcmHost | null;
  };
  deleteDialog: {
    host: AdcmHost | null;
  };
  maintenanceModeDialog: {
    host: AdcmHost | null;
  };
  linkDialog: {
    host: AdcmHost | null;
  };
  unlinkDialog: {
    host: AdcmHost | null;
  };
  relatedData: {
    clusters: AdcmCluster[];
    hostProviders: AdcmHostProvider[];
  };
  isActionInProgress: boolean;
}

const createInitialState = (): AdcmHostsActionsState => ({
  createDialog: {
    isOpen: false,
  },
  updateDialog: {
    host: null,
  },
  deleteDialog: {
    host: null,
  },
  maintenanceModeDialog: {
    host: null,
  },
  linkDialog: {
    host: null,
  },
  unlinkDialog: {
    host: null,
  },
  relatedData: {
    clusters: [],
    hostProviders: [],
  },
  isActionInProgress: false,
});

const hostsActionsSlice = createCrudSlice({
  name: 'adcm/hostsActions',
  entityName: 'host',
  createInitialState,
  reducers: {
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.host = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.host = null;
    },
    openLinkDialog(state, action) {
      state.linkDialog.host = action.payload;
    },
    closeLinkDialog(state) {
      state.linkDialog.host = null;
    },
    openUnlinkDialog(state, action) {
      state.unlinkDialog.host = action.payload;
    },
    closeUnlinkDialog(state) {
      state.unlinkDialog.host = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(toggleMaintenanceMode.pending, (state) => {
      hostsActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
    builder.addCase(unlinkHost.pending, (state) => {
      hostsActionsSlice.caseReducers.closeUnlinkDialog(state);
    });
    builder.addCase(linkHost.fulfilled, (state) => {
      hostsActionsSlice.caseReducers.closeLinkDialog(state);
    });
    builder.addCase(createHost.fulfilled, (state) => {
      hostsActionsSlice.caseReducers.closeCreateDialog(state);
    });
    builder.addCase(updateHost.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(getHosts.pending, () => {
      // hide actions dialogs, when load new hosts list (not silent refresh)
      hostsActionsSlice.caseReducers.cleanupActions();
    });
    builder.addCase(loadClusters.fulfilled, (state, action) => {
      state.relatedData.clusters = action.payload;
    });
    builder.addCase(loadClusters.rejected, (state) => {
      state.relatedData.clusters = [];
    });
    builder.addCase(loadHostProviders.fulfilled, (state, action) => {
      state.relatedData.hostProviders = action.payload;
    });
    builder.addCase(loadHostProviders.rejected, (state) => {
      state.relatedData.hostProviders = [];
    });
  },
});

export const {
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  openLinkDialog,
  closeLinkDialog,
  openUnlinkDialog,
  closeUnlinkDialog,
  openUpdateDialog,
  closeUpdateDialog,
  setIsActionInProgress,
} = hostsActionsSlice.actions;

export {
  unlinkHostWithUpdate,
  linkHostWithUpdate,
  loadClusters,
  loadHostProviders,
  createHost,
  createHostWithUpdate,
  deleteHost,
  deleteHostWithUpdate,
  toggleMaintenanceMode,
  updateHost,
};

export default hostsActionsSlice.reducer;
