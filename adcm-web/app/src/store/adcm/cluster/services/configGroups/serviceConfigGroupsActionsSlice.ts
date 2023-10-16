import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceConfigGroupsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import { AdcmClusterServiceConfigGroupCreateData } from '@api/adcm/clusterServiceGroupConfigs';
import { getClusterServiceConfigGroups } from './serviceConfigGroupsSlice';

interface AdcmClusterServiceConfigGroupActionsState {
  deleteDialog: {
    configGroup: AdcmConfigGroup | null;
  };
  createDialog: {
    isOpen: boolean;
    isCreating: boolean;
  };
  mappingDialog: {
    configGroup: AdcmConfigGroup | null;
    isSaveMapping: boolean;
  };
  relatedData: {
    candidatesHosts: AdcmHostCandidate[];
  };
}

type ClusterServiceConfigGroupPayload = {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
};

const deleteClusterServiceConfigGroup = createAsyncThunk(
  'adcm/cluster/service/clusterServiceConfigGroupActions/deleteConfigGroup',
  async ({ clusterId, serviceId, configGroupId }: ClusterServiceConfigGroupPayload, thunkAPI) => {
    try {
      await AdcmClusterServiceConfigGroupsApi.deleteConfigGroup(clusterId, serviceId, configGroupId);

      thunkAPI.dispatch(showInfo({ message: 'Config Group was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteClusterServiceConfigGroupWithUpdate = createAsyncThunk(
  'adcm/cluster/service/clusterServiceConfigGroupActions/deleteConfigGroupWithUpdate',
  async (arg: ClusterServiceConfigGroupPayload, thunkAPI) => {
    await thunkAPI.dispatch(deleteClusterServiceConfigGroup(arg)).unwrap();
    thunkAPI.dispatch(getClusterServiceConfigGroups(arg));
  },
);

type CreateClusterServiceConfigGroupPayload = {
  clusterId: number;
  serviceId: number;
  data: AdcmClusterServiceConfigGroupCreateData;
};

const createClusterServiceConfigGroup = createAsyncThunk(
  'adcm/cluster/service/clusterServiceConfigGroupActions/createConfigGroup',
  async ({ clusterId, serviceId, data }: CreateClusterServiceConfigGroupPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsCreating(true));
      return await AdcmClusterServiceConfigGroupsApi.createConfigGroup(clusterId, serviceId, data);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsCreating(false));
    }
  },
);

const getClusterServiceConfigGroupHostsCandidates = createAsyncThunk(
  'adcm/cluster/service/clusterServiceConfigGroupActions/getClusterServiceConfigGroupHostsCandidates',
  async ({ clusterId, serviceId, configGroupId }: ClusterServiceConfigGroupPayload, thunkAPI) => {
    try {
      return await AdcmClusterServiceConfigGroupsApi.getConfigGroupHostsCandidates(clusterId, serviceId, configGroupId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

type SaveClusterServiceConfigGroupMappedHostsPayload = ClusterServiceConfigGroupPayload & {
  mappedHostsIds: number[];
};

const saveClusterServiceConfigGroupMappedHosts = createAsyncThunk(
  'adcm/clusterConfigGroupActions/saveConfigGroupMappedHosts',
  async (
    { clusterId, serviceId, configGroupId, mappedHostsIds }: SaveClusterServiceConfigGroupMappedHostsPayload,
    thunkAPI,
  ) => {
    try {
      thunkAPI.dispatch(setIsSaveMapping(true));
      return await AdcmClusterServiceConfigGroupsApi.saveConfigGroupMappedHosts(
        clusterId,
        serviceId,
        configGroupId,
        mappedHostsIds,
      );
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(closeMappingDialog());
      thunkAPI.dispatch(getClusterServiceConfigGroups({ clusterId, serviceId }));
    }
  },
);

const createInitialState = (): AdcmClusterServiceConfigGroupActionsState => ({
  deleteDialog: {
    configGroup: null,
  },
  mappingDialog: {
    configGroup: null,
    isSaveMapping: false,
  },
  createDialog: {
    isOpen: false,
    isCreating: false,
  },
  relatedData: {
    candidatesHosts: [],
  },
});

const clusterServiceConfigGroupActionsSlice = createSlice({
  name: 'adcm/cluster/service/clusterServiceConfigGroupActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openDeleteDialog(state, action) {
      state.deleteDialog.configGroup = action.payload;
    },
    closeDeleteDialog(state) {
      state.deleteDialog.configGroup = null;
    },
    openCreateDialog(state) {
      state.createDialog.isOpen = true;
    },
    closeCreateDialog(state) {
      state.createDialog.isOpen = false;
      state.createDialog.isCreating = false;
    },
    openMappingDialog(state, action) {
      state.mappingDialog.configGroup = action.payload;
    },
    closeMappingDialog(state) {
      state.mappingDialog.configGroup = null;
      state.relatedData.candidatesHosts = [];
      state.mappingDialog.isSaveMapping = false;
    },
    setIsCreating(state, action) {
      state.createDialog.isCreating = action.payload;
    },
    setIsSaveMapping(state, action) {
      state.mappingDialog.isSaveMapping = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(createClusterServiceConfigGroup.fulfilled, (state) => {
        clusterServiceConfigGroupActionsSlice.caseReducers.closeCreateDialog(state);
      })
      .addCase(deleteClusterServiceConfigGroupWithUpdate.pending, (state) => {
        clusterServiceConfigGroupActionsSlice.caseReducers.closeDeleteDialog(state);
      })
      .addCase(getClusterServiceConfigGroupHostsCandidates.fulfilled, (state, action) => {
        state.relatedData.candidatesHosts = action.payload;
      })
      .addCase(getClusterServiceConfigGroupHostsCandidates.rejected, (state) => {
        state.relatedData.candidatesHosts = [];
      });
  },
});

const {
  cleanupActions,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  setIsCreating,
  openMappingDialog,
  closeMappingDialog,
  setIsSaveMapping,
} = clusterServiceConfigGroupActionsSlice.actions;

export {
  cleanupActions,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  openMappingDialog,
  closeMappingDialog,
};
export default clusterServiceConfigGroupActionsSlice.reducer;

export {
  createClusterServiceConfigGroup,
  deleteClusterServiceConfigGroupWithUpdate,
  getClusterServiceConfigGroupHostsCandidates,
  saveClusterServiceConfigGroupMappedHosts,
};
