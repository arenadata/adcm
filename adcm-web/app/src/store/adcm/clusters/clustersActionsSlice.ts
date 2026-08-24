import type { RequestError } from '@api';
import { AdcmClustersApi, AdcmPrototypesApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { refreshClusters, upsertCluster, removeCluster } from './clustersSlice';
import { setCluster } from './clusterSlice';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import {
  AdcmPrototypeType,
  type AdcmCluster,
  type AdcmPrototypeVersions,
  type CreateAdcmClusterPayload,
  type AdcmRenameArgs,
  type AdcmEditDescriptionArgs,
} from '@models/adcm';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';
import type { ModalState } from '@models/modal';
import { excludeUnsupportedPrototypeVersions } from '@utils/contractVersionUtils';
import { setSelectedClusterId } from './clustersViewSlice';

interface AdcmClusterActionsState extends ModalState<AdcmCluster, 'cluster'> {
  createDialog: {
    isOpen: boolean;
  };
  deleteDialog: {
    cluster: AdcmCluster | null;
  };
  updateDialog: {
    cluster: AdcmCluster | null;
  };
  descriptionDialog: {
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

const loadPrototypeVersions = createAsyncThunk('adcm/clustersActions/loadPrototypeVersions', async (_arg, thunkAPI) => {
  try {
    const prototypeVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Cluster });
    return excludeUnsupportedPrototypeVersions(prototypeVersions);
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const loadPrototypesRelatedData = createAsyncThunk('adcm/clustersActions/loadRelatedData', async (_arg, thunkAPI) => {
  await thunkAPI.dispatch(loadPrototypeVersions());
});

const deleteClusterWithUpdate = createAsyncThunk(
  'adcm/clustersActions/deleteClusterWithUpdate',
  async (clusterId: number, thunkAPI) => {
    const {
      adcm: {
        clustersView: { selectedClusterId },
      },
    } = thunkAPI.getState();

    if (selectedClusterId === clusterId) {
      thunkAPI.dispatch(setSelectedClusterId(null));
    }
    // Remove immediately so WS concern-delete events don't flash empty concerns in the preview.
    thunkAPI.dispatch(removeCluster(clusterId));

    try {
      await AdcmClustersApi.deleteCluster(clusterId);
      await thunkAPI.dispatch(refreshClusters());
      thunkAPI.dispatch(showSuccess({ message: 'The cluster has been deleted' }));
    } catch (error) {
      await thunkAPI.dispatch(refreshClusters());
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const renameClusterWithUpdate = createAsyncThunk(
  'adcm/clustersActions/renameClusterWithUpdate',
  async ({ id, name }: AdcmRenameArgs, thunkAPI) => {
    try {
      const cluster = await AdcmClustersApi.patchCluster(id, { name });
      thunkAPI.dispatch(upsertCluster(cluster));
      thunkAPI.dispatch(setCluster(cluster));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const editClusterDescriptionWithUpdate = createAsyncThunk(
  'adcm/clustersActions/editClusterDescriptionWithUpdate',
  async ({ id, description }: AdcmEditDescriptionArgs, thunkAPI) => {
    try {
      const cluster = await AdcmClustersApi.patchCluster(id, { description });
      thunkAPI.dispatch(upsertCluster(cluster));
      thunkAPI.dispatch(setCluster(cluster));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmClusterActionsState => ({
  createDialog: {
    isOpen: false,
  },
  updateDialog: {
    cluster: null,
  },
  deleteDialog: {
    cluster: null,
  },
  descriptionDialog: {
    cluster: null,
  },
  relatedData: {
    prototypeVersions: [],
    isLoaded: false,
  },
});

const clustersActionsSlice = createCrudSlice({
  name: 'adcm/clustersActions',
  entityName: 'cluster',
  createInitialState,
  reducers: {
    cleanupClustersActions() {
      return createInitialState();
    },
    openClusterRenameDialog(state, action) {
      state.updateDialog.cluster = action.payload;
    },
    closeClusterRenameDialog(state) {
      state.updateDialog.cluster = null;
    },
    openClusterDescriptionChangeDialog(state, action) {
      state.descriptionDialog.cluster = action.payload;
    },
    closeClusterDescriptionChangeDialog(state) {
      state.descriptionDialog.cluster = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(loadPrototypesRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.prototypeVersions = action.payload;
    });
    builder.addCase(createCluster.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(renameClusterWithUpdate.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(editClusterDescriptionWithUpdate.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(deleteClusterWithUpdate.pending, (state) => {
      clustersActionsSlice.caseReducers.closeDeleteDialog(state);
    });
  },
});

const {
  cleanupClustersActions,
  openClusterRenameDialog,
  closeClusterRenameDialog,
  openClusterDescriptionChangeDialog,
  closeClusterDescriptionChangeDialog,
  openCreateDialog,
  openUpdateDialog,
  openDeleteDialog,
  closeDeleteDialog,
} = clustersActionsSlice.actions;
export {
  createCluster,
  renameClusterWithUpdate as renameCluster,
  editClusterDescriptionWithUpdate as editDescription,
  deleteClusterWithUpdate,
  cleanupClustersActions,
  openClusterRenameDialog,
  closeClusterRenameDialog,
  openClusterDescriptionChangeDialog,
  closeClusterDescriptionChangeDialog,
  openCreateDialog,
  openUpdateDialog,
  openDeleteDialog,
  closeDeleteDialog,
  loadPrototypesRelatedData,
};
export default clustersActionsSlice.reducer;
