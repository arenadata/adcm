import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getHosts, setHostMaintenanceMode } from '@store/adcm/hosts/hostsSlice';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { RequestError } from '@api';
import { AdcmClustersApi, AdcmHostProvidersApi, AdcmHostsApi } from '@api';
import type {
  AdcmCluster,
  AdcmHost,
  AdcmHostProvider,
  AdcmRenameArgs,
  CreateAdcmHostPayload,
  CreateHostDuplicatePayload,
} from '@models/adcm';
import { AdcmMaintenanceMode } from '@models/adcm';
import type { SortParams } from '@models/table';
import { unlimitedRequestItems } from '@constants';
import { arePromisesResolved } from '@utils/promiseUtils';

const loadClusters = createAsyncThunk('adcm/hostsActions/loadClusters', async (_arg, thunkAPI) => {
  try {
    const clusters = await AdcmClustersApi.getClusters(undefined, undefined, {
      pageNumber: 0,
      perPage: unlimitedRequestItems,
    });
    return clusters.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const loadHostProviders = createAsyncThunk('adcm/hostsActions/hostProviders', async (_arg, thunkAPI) => {
  try {
    const emptyFilter = {};
    const defaultSortParams: SortParams = { sortBy: 'name', sortDirection: 'asc' };

    const hostProviders = await AdcmHostProvidersApi.getHostProviders(emptyFilter, defaultSortParams);
    return hostProviders.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

interface LinkHostsPayload {
  clusterId: number;
  hostIds: number[];
}

const unlinkHosts = createAsyncThunk('adcm/hostsActions/unlinkHosts', async (hosts: AdcmHost[], thunkAPI) => {
  try {
    arePromisesResolved(
      await Promise.allSettled(hosts.map(({ id: hostId, cluster }) => AdcmClustersApi.unlinkHost(cluster.id, hostId))),
    );
    const message = hosts.length > 1 ? 'All selected hosts have been unlinked' : 'The host has been unlinked';
    thunkAPI.dispatch(showSuccess({ message }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const unlinkHostsWithUpdate = createAsyncThunk(
  'adcm/hostsActions/unlinkHostsWithUpdate',
  async (hosts: AdcmHost[], thunkAPI) => {
    // Do not use .unwrap() so getHosts() runs even on partial failure
    await thunkAPI.dispatch(unlinkHosts(hosts));
    thunkAPI.dispatch(getHosts());
  },
);

const linkHosts = createAsyncThunk(
  'adcm/hostsActions/linkHosts',
  async ({ clusterId, hostIds }: LinkHostsPayload, thunkAPI) => {
    try {
      await AdcmClustersApi.linkHost(clusterId, hostIds);
      const message = hostIds.length > 1 ? 'All selected hosts have been linked' : 'The host has been linked';
      thunkAPI.dispatch(showSuccess({ message }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const linkHostsWithUpdate = createAsyncThunk(
  'adcm/hostsActions/linkHostsWithUpdate',
  async (arg: LinkHostsPayload, thunkAPI) => {
    await thunkAPI.dispatch(linkHosts(arg)).unwrap();
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

const createHostDuplicate = createAsyncThunk(
  'adcm/hostsActions/createHostDublicate',
  async (payload: CreateHostDuplicatePayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsActionInProgress(true));
      const host = await AdcmHostsApi.createDuplicateHost(payload);
      return host;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsActionInProgress(false));
    }
  },
);

const createHostDuplicateWithUpdate = createAsyncThunk(
  'adcm/hostsActions/createHostDuplicateWithUpdate',
  async (payload: CreateHostDuplicatePayload, thunkAPI) => {
    await thunkAPI.dispatch(createHostDuplicate(payload)).unwrap();
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

const deleteHosts = createAsyncThunk('adcm/hostsActions/deleteHosts', async (hostIds: number[], thunkAPI) => {
  try {
    arePromisesResolved(await Promise.allSettled(hostIds.map((hostId) => AdcmHostsApi.deleteHost(hostId))));
    const message = hostIds.length > 1 ? 'All selected hosts have been deleted' : 'The host has been deleted';
    thunkAPI.dispatch(showSuccess({ message }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const deleteHostsWithUpdate = createAsyncThunk(
  'adcm/hostsActions/deleteHostsWithUpdate',
  async (hostIds: number[], thunkAPI) => {
    // Do not use .unwrap() so getHosts() runs even on partial failure
    await thunkAPI.dispatch(deleteHosts(hostIds));
    thunkAPI.dispatch(getHosts());
  },
);

const updateHost = createAsyncThunk('adcm/hostsActions/updateHost', async ({ id, name }: AdcmRenameArgs, thunkAPI) => {
  try {
    await AdcmHostsApi.patchHost(id, { name });
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const updateHostWithUpdate = createAsyncThunk(
  'adcm/hostsActions/updateHostWithUpdate',
  async (arg: AdcmRenameArgs, thunkAPI) => {
    await thunkAPI.dispatch(updateHost(arg)).unwrap();
  },
);

interface AdcmHostsActionsState {
  createDialog: {
    isOpen: boolean;
  };
  updateDialog: {
    host: AdcmHost | null;
  };
  deleteDialog: {
    hosts: AdcmHost[];
  };
  maintenanceModeDialog: {
    host: AdcmHost | null;
  };
  linkDialog: {
    hosts: AdcmHost[];
  };
  unlinkDialog: {
    hosts: AdcmHost[];
  };
  hostSharingDialog: {
    host: AdcmHost | null;
  };
  relatedData: {
    clusters: AdcmCluster[];
    hostProviders: AdcmHostProvider[];
  };
  selectedItemsIds: number[];
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
    hosts: [],
  },
  maintenanceModeDialog: {
    host: null,
  },
  linkDialog: {
    hosts: [],
  },
  unlinkDialog: {
    hosts: [],
  },
  hostSharingDialog: {
    host: null,
  },
  relatedData: {
    clusters: [],
    hostProviders: [],
  },
  selectedItemsIds: [],
  isActionInProgress: false,
});

const hostsActionsSlice = createSlice({
  name: 'adcm/hostsActions',
  initialState: createInitialState,
  reducers: {
    setIsActionInProgress(state, action: PayloadAction<boolean>) {
      state.isActionInProgress = action.payload;
    },
    openCreateDialog(state) {
      state.createDialog.isOpen = true;
    },
    closeCreateDialog(state) {
      state.createDialog.isOpen = false;
    },
    openUpdateDialog(state, action: PayloadAction<AdcmHost>) {
      state.updateDialog.host = action.payload;
    },
    closeUpdateDialog(state) {
      state.updateDialog.host = null;
    },
    openDeleteDialog(state, action: PayloadAction<AdcmHost[]>) {
      state.deleteDialog.hosts = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.hosts = [];
    },
    cleanupActions() {
      return createInitialState();
    },
    openMaintenanceModeDialog(state, action: PayloadAction<AdcmHost>) {
      state.maintenanceModeDialog.host = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.host = null;
    },
    openLinkDialog(state, action: PayloadAction<AdcmHost[]>) {
      state.linkDialog.hosts = action.payload;
    },
    closeLinkDialog(state) {
      state.linkDialog.hosts = [];
    },
    openUnlinkDialog(state, action: PayloadAction<AdcmHost[]>) {
      state.unlinkDialog.hosts = action.payload;
    },
    closeUnlinkDialog(state) {
      state.unlinkDialog.hosts = [];
    },
    openHostSharingDialog(state, action) {
      state.hostSharingDialog.host = action.payload;
    },
    closeHostSharingDialog(state) {
      state.hostSharingDialog.host = null;
    },
    setSelectedItemsIds(state, action) {
      state.selectedItemsIds = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(toggleMaintenanceMode.pending, (state) => {
      hostsActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
    builder.addCase(createHostDuplicate.pending, (state) => {
      hostsActionsSlice.caseReducers.closeHostSharingDialog(state);
    });
    builder.addCase(createHost.fulfilled, (state) => {
      hostsActionsSlice.caseReducers.closeCreateDialog(state);
    });
    builder.addCase(deleteHosts.pending, (state) => {
      state.selectedItemsIds = [];
      hostsActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    builder.addCase(unlinkHosts.pending, (state) => {
      state.selectedItemsIds = [];
      hostsActionsSlice.caseReducers.closeUnlinkDialog(state);
    });
    builder.addCase(linkHosts.pending, (state) => {
      state.selectedItemsIds = [];
      hostsActionsSlice.caseReducers.closeLinkDialog(state);
    });
    builder.addCase(updateHost.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(getHosts.pending, () => {
      // hide actions dialogs, when load new hosts list (not silent refresh)
      hostsActionsSlice.caseReducers.cleanupActions();
    });
    builder.addCase(getHosts.fulfilled, (state) => {
      state.selectedItemsIds = [];
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
  openHostSharingDialog,
  closeHostSharingDialog,
  setSelectedItemsIds,
  cleanupActions,
} = hostsActionsSlice.actions;

export {
  unlinkHostsWithUpdate,
  linkHostsWithUpdate,
  loadClusters,
  loadHostProviders,
  createHost,
  createHostWithUpdate,
  deleteHosts,
  deleteHostsWithUpdate,
  toggleMaintenanceMode,
  updateHostWithUpdate as updateHost,
  createHostDuplicateWithUpdate as createHostDuplicate,
};

export default hostsActionsSlice.reducer;
