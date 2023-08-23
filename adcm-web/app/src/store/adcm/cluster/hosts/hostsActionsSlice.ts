import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { AdcmClusterHostsApi, AdcmClustersApi, AdcmHostsApi, RequestError } from '@api';
import { showError } from '@store/notificationsSlice.ts';
import { getErrorMessage } from '@utils/httpResponseUtils.ts';
import { getHosts } from '@store/adcm/hosts/hostsSlice.ts';
import { AdcmHost } from '@models/adcm';
import { AddClusterHostsPayload } from '@models/adcm';

const loadHosts = createAsyncThunk('adcm/clusterHostsActions/loadHosts', async (arg, thunkAPI) => {
  try {
    const hosts = await AdcmHostsApi.getHosts();
    return hosts.results;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

interface UnlinkHostTogglePayload {
  hostId: number;
  clusterId: number;
}

const unlinkHost = createAsyncThunk(
  'adcm/clusterHostsActions/unlinkHost',
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

const addClusterHosts = createAsyncThunk(
  'adcm/clusterHostsActions/addClusterHosts',
  async ({ clusterId, hostIds }: AddClusterHostsPayload, thunkAPI) => {
    try {
      const host = await AdcmClusterHostsApi.addClusterHosts({ clusterId, hostIds });
      return host;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getHosts());
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
    },
  },
  extraReducers: (builder) => {
    builder.addCase(unlinkHost.pending, (state) => {
      clusterHostsActionsSlice.caseReducers.closeUnlinkDialog(state);
    });
    builder.addCase(addClusterHosts.fulfilled, (state) => {
      clusterHostsActionsSlice.caseReducers.closeAddDialog(state);
    });
    builder.addCase(getHosts.pending, () => {
      // hide actions dialogs, when load new hosts list (not silent refresh)
      clusterHostsActionsSlice.caseReducers.cleanupActions();
    });
    builder.addCase(loadHosts.fulfilled, (state, action) => {
      state.relatedData.hosts = action.payload;
    });
    builder.addCase(loadHosts.rejected, (state) => {
      state.relatedData.hosts = [];
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

export { unlinkHost, loadHosts, addClusterHosts };

export default clusterHostsActionsSlice.reducer;
