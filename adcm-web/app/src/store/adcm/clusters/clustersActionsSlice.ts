import { AdcmClustersApi, AdcmPrototypesApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { refreshClusters } from './clustersSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { createSlice } from '@reduxjs/toolkit';
import {
  AdcmCluster,
  AdcmPrototypeType,
  AdcmPrototypeVersions,
  CreateAdcmClusterPayload,
  AdcmRenameArgs,
} from '@models/adcm';

interface AdcmClusterActionsState {
  cluster: AdcmCluster | undefined;
  isCreateClusterDialogOpen: boolean;
  isUpgradeClusterDialogOpen: boolean;
  deletableId: {
    id: number | null;
  };
  updateDialog: {
    cluster: AdcmCluster | null;
  };
  relatedData: {
    prototypeVersions: AdcmPrototypeVersions[];
    isLoaded: boolean;
  };
}

type CreateAdcmClusterWithLicensePayload = CreateAdcmClusterPayload & {
  isNeedAcceptLicense: boolean;
};

const createCluster = createAsyncThunk(
  'adcm/clustersActions/createCluster',
  async ({ isNeedAcceptLicense, ...arg }: CreateAdcmClusterWithLicensePayload, thunkAPI) => {
    try {
      if (isNeedAcceptLicense) {
        await AdcmPrototypesApi.postAcceptLicense(arg.prototypeId);
      }

      const cluster = await AdcmClustersApi.postCluster(arg);
      return cluster;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(refreshClusters());
    }
  },
);

const loadPrototypeVersions = createAsyncThunk('adcm/clustersActions/loadPrototypeVersions', async (arg, thunkAPI) => {
  try {
    const prototypeVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Cluster });
    return prototypeVersions;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const loadPrototypesRelatedData = createAsyncThunk('adcm/clustersActions/loadRelatedData', async (arg, thunkAPI) => {
  await thunkAPI.dispatch(loadPrototypeVersions());
});

const openClusterCreateDialog = createAsyncThunk(
  'adcm/clustersActions/openClusterCreateDialog',
  async (arg, thunkAPI) => {
    try {
      thunkAPI.dispatch(loadPrototypesRelatedData());
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteClusterWithUpdate = createAsyncThunk(
  'adcm/clustersActions/deleteClusterWithUpdate',
  async (clusterId: number, thunkAPI) => {
    try {
      await AdcmClustersApi.deleteCluster(clusterId);
      await thunkAPI.dispatch(refreshClusters());
      thunkAPI.dispatch(showInfo({ message: 'The cluster has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const renameCluster = createAsyncThunk(
  'adcm/clustersActions/renameCluster',
  async ({ id, name }: AdcmRenameArgs, thunkAPI) => {
    try {
      return await AdcmClustersApi.patchCluster(id, { name });
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(refreshClusters());
    }
  },
);

const createInitialState = (): AdcmClusterActionsState => ({
  cluster: undefined,
  isCreateClusterDialogOpen: false,
  isUpgradeClusterDialogOpen: false,
  relatedData: {
    prototypeVersions: [],
    isLoaded: false,
  },
  deletableId: {
    id: null,
  },
  updateDialog: {
    cluster: null,
  },
});

const clustersActionsSlice = createSlice({
  name: 'adcm/clustersActions',
  initialState: createInitialState(),
  reducers: {
    cleanupClustersActions() {
      return createInitialState();
    },
    openClusterDeleteDialog(state, action) {
      state.deletableId.id = action.payload;
    },
    closeClusterDeleteDialog(state) {
      state.deletableId.id = null;
    },
    openClusterRenameDialog(state, action) {
      state.updateDialog.cluster = action.payload;
    },
    closeClusterRenameDialog(state) {
      state.updateDialog.cluster = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(openClusterCreateDialog.fulfilled, (state) => {
      state.isCreateClusterDialogOpen = true;
    });
    builder.addCase(loadPrototypesRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.prototypeVersions = action.payload;
    });
    builder.addCase(createCluster.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(renameCluster.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(deleteClusterWithUpdate.pending, (state) => {
      clustersActionsSlice.caseReducers.closeClusterDeleteDialog(state);
    });
  },
});

const {
  openClusterDeleteDialog,
  closeClusterDeleteDialog,
  cleanupClustersActions,
  openClusterRenameDialog,
  closeClusterRenameDialog,
} = clustersActionsSlice.actions;
export {
  createCluster,
  renameCluster,
  openClusterCreateDialog,
  deleteClusterWithUpdate,
  openClusterDeleteDialog,
  closeClusterDeleteDialog,
  cleanupClustersActions,
  openClusterRenameDialog,
  closeClusterRenameDialog,
};
export default clustersActionsSlice.reducer;
