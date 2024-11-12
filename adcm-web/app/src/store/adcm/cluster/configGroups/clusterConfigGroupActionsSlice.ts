import { createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { AdcmClusterConfigGroupsApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import type { AdcmClusterConfigGroupCreateData } from '@api/adcm/clusterGroupConfig';
import { getClusterConfigGroups } from '@store/adcm/cluster/configGroups/clusterConfigGroupsSlice';
import { mappedHostsToConfigGroup } from '@store/adcm/entityConfiguration/configGroupSlice.utils';

interface AdcmClusterConfigGroupActionsState {
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

type ClusterConfigGroupPayload = {
  clusterId: number;
  configGroupId: number;
};

const deleteClusterConfigGroup = createAsyncThunk(
  'adcm/clusterConfigGroupActions/deleteConfigGroup',
  async ({ clusterId, configGroupId }: ClusterConfigGroupPayload, thunkAPI) => {
    try {
      await AdcmClusterConfigGroupsApi.deleteConfigGroup(clusterId, configGroupId);

      thunkAPI.dispatch(showSuccess({ message: 'Config Group was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteClusterConfigGroupWithUpdate = createAsyncThunk(
  'adcm/clusterConfigGroupActions/deleteConfigGroupWithUpdate',
  async (arg: ClusterConfigGroupPayload, thunkAPI) => {
    await thunkAPI.dispatch(deleteClusterConfigGroup(arg)).unwrap();
    thunkAPI.dispatch(getClusterConfigGroups(arg.clusterId));
  },
);

type CreateClusterConfigGroupPayload = {
  clusterId: number;
  data: AdcmClusterConfigGroupCreateData;
};

const createClusterConfigGroup = createAsyncThunk(
  'adcm/clusterConfigGroupActions/createConfigGroup',
  async ({ clusterId, data }: CreateClusterConfigGroupPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsCreating(true));
      return await AdcmClusterConfigGroupsApi.createConfigGroup(clusterId, data);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsCreating(false));
    }
  },
);

const getClusterConfigGroupHostsCandidates = createAsyncThunk(
  'adcm/clusterConfigGroupActions/getConfigGroupHostsCandidates',
  async ({ clusterId, configGroupId }: ClusterConfigGroupPayload, thunkAPI) => {
    try {
      return await AdcmClusterConfigGroupsApi.getConfigGroupHostsCandidates(clusterId, configGroupId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

type SaveClusterConfigGroupMappedHostsPayload = ClusterConfigGroupPayload & {
  mappedHostsIds: number[];
};

const saveClusterConfigGroupMappedHosts = createAsyncThunk(
  'adcm/clusterConfigGroupActions/saveConfigGroupMappedHosts',
  async ({ clusterId, mappedHostsIds }: SaveClusterConfigGroupMappedHostsPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsSaveMapping(true));

      const {
        adcm: {
          clusterConfigGroupActions: {
            mappingDialog: { configGroup },
          },
        },
      } = thunkAPI.getState();

      const isMappingFullSuccess = await mappedHostsToConfigGroup({
        configGroup,
        mappedHostsIds,
        appendHost: (configGroupId, hostId) =>
          AdcmClusterConfigGroupsApi.mappedHostToConfigGroup(clusterId, configGroupId, hostId),
        removeHost: (configGroupId, hostId) =>
          AdcmClusterConfigGroupsApi.unmappedHostToConfigGroup(clusterId, configGroupId, hostId),
        dispatch: thunkAPI.dispatch,
      });

      return thunkAPI.fulfillWithValue(isMappingFullSuccess);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(closeMappingDialog());
      thunkAPI.dispatch(getClusterConfigGroups(clusterId));
    }
  },
);

const createInitialState = (): AdcmClusterConfigGroupActionsState => ({
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

const clusterConfigGroupActionsSlice = createSlice({
  name: 'adcm/clusterConfigGroupActions',
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
      .addCase(createClusterConfigGroup.fulfilled, (state) => {
        clusterConfigGroupActionsSlice.caseReducers.closeCreateDialog(state);
      })
      .addCase(deleteClusterConfigGroupWithUpdate.pending, (state) => {
        clusterConfigGroupActionsSlice.caseReducers.closeDeleteDialog(state);
      })
      .addCase(getClusterConfigGroupHostsCandidates.fulfilled, (state, action) => {
        state.relatedData.candidatesHosts = action.payload;
      })
      .addCase(getClusterConfigGroupHostsCandidates.rejected, (state) => {
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
} = clusterConfigGroupActionsSlice.actions;

export {
  cleanupActions,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  openMappingDialog,
  closeMappingDialog,
};
export default clusterConfigGroupActionsSlice.reducer;

export {
  createClusterConfigGroup,
  deleteClusterConfigGroupWithUpdate,
  getClusterConfigGroupHostsCandidates,
  saveClusterConfigGroupMappedHosts,
};
