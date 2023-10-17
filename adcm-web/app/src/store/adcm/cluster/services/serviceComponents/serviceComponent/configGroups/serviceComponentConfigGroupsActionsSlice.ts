import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterServiceComponentConfigGroupsApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import { AdcmServiceComponentConfigGroupCreateData } from '@api/adcm/serviceComponentGroupConfigs';
import { getServiceComponentConfigGroups } from './serviceComponentConfigGroupsSlice';

interface AdcmServiceComponentConfigGroupActionsState {
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

type ServiceComponentParentArgs = {
  clusterId: number;
  serviceId: number;
  componentId: number;
};

type ServiceComponentConfigGroupPayload = ServiceComponentParentArgs & {
  configGroupId: number;
};

const deleteServiceComponentConfigGroup = createAsyncThunk(
  'adcm/serviceComponentConfigGroupActions/deleteConfigGroup',
  async ({ clusterId, serviceId, componentId, configGroupId }: ServiceComponentConfigGroupPayload, thunkAPI) => {
    try {
      await AdcmClusterServiceComponentConfigGroupsApi.deleteConfigGroup(
        clusterId,
        serviceId,
        componentId,
        configGroupId,
      );

      thunkAPI.dispatch(showInfo({ message: 'Config Group was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteServiceComponentConfigGroupWithUpdate = createAsyncThunk(
  'adcm/serviceComponentConfigGroupActions/deleteConfigGroupWithUpdate',
  async (arg: ServiceComponentConfigGroupPayload, thunkAPI) => {
    await thunkAPI.dispatch(deleteServiceComponentConfigGroup(arg)).unwrap();
    thunkAPI.dispatch(getServiceComponentConfigGroups(arg));
  },
);

type CreateServiceComponentConfigGroupPayload = ServiceComponentParentArgs & {
  data: AdcmServiceComponentConfigGroupCreateData;
};

const createServiceComponentConfigGroup = createAsyncThunk(
  'adcm/serviceComponentConfigGroupActions/createConfigGroup',
  async ({ clusterId, serviceId, componentId, data }: CreateServiceComponentConfigGroupPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsCreating(true));
      return await AdcmClusterServiceComponentConfigGroupsApi.createConfigGroup(
        clusterId,
        serviceId,
        componentId,
        data,
      );
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsCreating(false));
    }
  },
);

const getServiceComponentConfigGroupHostsCandidates = createAsyncThunk(
  'adcm/serviceComponentConfigGroupActions/getServiceComponentConfigGroupHostsCandidates',
  async ({ clusterId, serviceId, componentId, configGroupId }: ServiceComponentConfigGroupPayload, thunkAPI) => {
    try {
      return await AdcmClusterServiceComponentConfigGroupsApi.getConfigGroupHostsCandidates(
        clusterId,
        serviceId,
        componentId,
        configGroupId,
      );
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

type SaveServiceComponentConfigGroupMappedHostsPayload = ServiceComponentConfigGroupPayload & {
  mappedHostsIds: number[];
};

const saveServiceComponentConfigGroupMappedHosts = createAsyncThunk(
  'adcm/serviceComponentConfigGroupActions/saveConfigGroupMappedHosts',
  async (
    {
      clusterId,
      serviceId,
      componentId,
      configGroupId,
      mappedHostsIds,
    }: SaveServiceComponentConfigGroupMappedHostsPayload,
    thunkAPI,
  ) => {
    try {
      thunkAPI.dispatch(setIsSaveMapping(true));
      return await AdcmClusterServiceComponentConfigGroupsApi.saveConfigGroupMappedHosts(
        clusterId,
        serviceId,
        componentId,
        configGroupId,
        mappedHostsIds,
      );
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(closeMappingDialog());
      thunkAPI.dispatch(getServiceComponentConfigGroups({ clusterId, serviceId, componentId }));
    }
  },
);

const createInitialState = (): AdcmServiceComponentConfigGroupActionsState => ({
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

const serviceComponentConfigGroupActionsSlice = createSlice({
  name: 'adcm/serviceComponentConfigGroupActions',
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
      .addCase(createServiceComponentConfigGroup.fulfilled, (state) => {
        serviceComponentConfigGroupActionsSlice.caseReducers.closeCreateDialog(state);
      })
      .addCase(deleteServiceComponentConfigGroupWithUpdate.pending, (state) => {
        serviceComponentConfigGroupActionsSlice.caseReducers.closeDeleteDialog(state);
      })
      .addCase(getServiceComponentConfigGroupHostsCandidates.fulfilled, (state, action) => {
        state.relatedData.candidatesHosts = action.payload;
      })
      .addCase(getServiceComponentConfigGroupHostsCandidates.rejected, (state) => {
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
} = serviceComponentConfigGroupActionsSlice.actions;

export {
  cleanupActions,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  openMappingDialog,
  closeMappingDialog,
};
export default serviceComponentConfigGroupActionsSlice.reducer;

export {
  createServiceComponentConfigGroup,
  deleteServiceComponentConfigGroupWithUpdate,
  getServiceComponentConfigGroupHostsCandidates,
  saveServiceComponentConfigGroupMappedHosts,
};
