import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getHosts } from '@store/adcm/hosts/hostsSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmClustersApi, AdcmHostProvidersApi, AdcmHostsApi, RequestError } from '@api';
import { AdcmCluster, AdcmHostProvider, CreateAdcmHostPayload } from '@models/adcm';
import { SortParams } from '@models/table';
import { rejectedFilter } from '@utils/promiseUtils';

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

interface UnlinkHostTogglePayload {
  hostId: number;
  clusterId: number;
}

const unlinkHost = createAsyncThunk(
  'adcm/hostsActions/unlinkHost',
  async ({ hostId, clusterId }: UnlinkHostTogglePayload, thunkAPI) => {
    try {
      await AdcmClustersApi.unlinkHost(clusterId, hostId);
      return thunkAPI.fulfillWithValue(null);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getHosts());
    }
  },
);

const linkHost = createAsyncThunk(
  'adcm/hostsActions/linkHost',
  async ({ hostId, clusterId }: UnlinkHostTogglePayload, thunkAPI) => {
    try {
      await AdcmClustersApi.linkHost(clusterId, hostId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getHosts());
    }
  },
);

const createHost = createAsyncThunk(
  'adcm/hostsActions/createHost',
  async (payload: CreateAdcmHostPayload, thunkAPI) => {
    try {
      const host = await AdcmHostsApi.createHost(payload);
      return host;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getHosts());
    }
  },
);

const deleteHosts = createAsyncThunk('adcm/hostsActions/deleteHosts', async (ids: number[], thunkAPI) => {
  try {
    const deletePromises = await Promise.allSettled(ids.map((id) => AdcmHostsApi.deleteHost(id)));
    const responsesList = rejectedFilter(deletePromises);

    if (responsesList.length > 0) {
      throw responsesList[0];
    }
    thunkAPI.dispatch(showInfo({ message: 'All selected hosts were deleted' }));
    return [];
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue([]);
  } finally {
    thunkAPI.dispatch(getHosts());
  }
});

interface AdcmHostsActionsState {
  deleteDialog: {
    id: number | null;
  };
  createDialog: {
    isOpen: boolean;
  };
  linkDialog: {
    id: null;
  };
  unlinkDialog: {
    id: null;
  };
  relatedData: {
    clusters: AdcmCluster[];
    hostProviders: AdcmHostProvider[];
  };
}

const createInitialState = (): AdcmHostsActionsState => ({
  deleteDialog: {
    id: null,
  },
  createDialog: {
    isOpen: false,
  },
  linkDialog: {
    id: null,
  },
  unlinkDialog: {
    id: null,
  },
  relatedData: {
    clusters: [],
    hostProviders: [],
  },
});

const hostsActionsSlice = createSlice({
  name: 'adcm/hostsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.id = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.id = null;
    },
    openLinkDialog(state, action) {
      state.linkDialog.id = action.payload;
    },
    closeLinkDialog(state) {
      state.linkDialog.id = null;
    },
    openUnlinkDialog(state, action) {
      state.unlinkDialog.id = action.payload;
    },
    closeUnlinkDialog(state) {
      state.unlinkDialog.id = null;
    },
    openCreateDialog(state) {
      state.createDialog.isOpen = true;
    },
    closeCreateDialog(state) {
      state.createDialog.isOpen = false;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(unlinkHost.pending, (state) => {
      hostsActionsSlice.caseReducers.closeUnlinkDialog(state);
    });
    builder.addCase(linkHost.fulfilled, (state) => {
      hostsActionsSlice.caseReducers.closeLinkDialog(state);
    });
    builder.addCase(createHost.fulfilled, (state) => {
      hostsActionsSlice.caseReducers.closeCreateDialog(state);
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
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  openLinkDialog,
  closeLinkDialog,
  openUnlinkDialog,
  closeUnlinkDialog,
} = hostsActionsSlice.actions;

export { unlinkHost, linkHost, loadClusters, loadHostProviders, createHost, deleteHosts };

export default hostsActionsSlice.reducer;
