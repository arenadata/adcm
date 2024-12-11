import type { RequestError } from '@api';
import { AdcmClustersApi, AdcmPrototypesApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { refreshClusters } from './clustersSlice';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import {
  AdcmPrototypeType,
  type AdcmCluster,
  type AdcmPrototypeVersions,
  type CreateAdcmClusterPayload,
  type AdcmRenameArgs,
} from '@models/adcm';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';
import type { ModalState } from '@models/modal';

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
    return prototypeVersions;
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
    try {
      await AdcmClustersApi.deleteCluster(clusterId);
      await thunkAPI.dispatch(refreshClusters());
      thunkAPI.dispatch(showSuccess({ message: 'The cluster has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const renameClusterWithUpdate = createAsyncThunk(
  'adcm/clustersActions/renameClusterWithUpdate',
  async ({ id, name }: AdcmRenameArgs, thunkAPI) => {
    try {
      await AdcmClustersApi.patchCluster(id, { name });
      await thunkAPI.dispatch(refreshClusters());
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
    builder.addCase(deleteClusterWithUpdate.pending, (state) => {
      clustersActionsSlice.caseReducers.closeDeleteDialog(state);
    });
  },
});

const {
  cleanupClustersActions,
  openClusterRenameDialog,
  closeClusterRenameDialog,
  openCreateDialog,
  openUpdateDialog,
  openDeleteDialog,
  closeDeleteDialog,
} = clustersActionsSlice.actions;
export {
  createCluster,
  renameClusterWithUpdate as renameCluster,
  deleteClusterWithUpdate,
  cleanupClustersActions,
  openClusterRenameDialog,
  closeClusterRenameDialog,
  openCreateDialog,
  openUpdateDialog,
  openDeleteDialog,
  closeDeleteDialog,
  loadPrototypesRelatedData,
};
export default clustersActionsSlice.reducer;
