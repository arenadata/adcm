import { createSlice } from '@reduxjs/toolkit';
import type { RequestError } from '@api';
import { AdcmHostProviderConfigGroupsApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import type { AdcmConfigGroup, AdcmHostCandidate } from '@models/adcm';
import type { AdcmHostProviderConfigGroupCreateData } from '@api/adcm/hostProviderGroupConfig';
import { getHostProviderConfigGroups } from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupsSlice';
import { mappedHostsToConfigGroup } from '@store/adcm/entityConfiguration/configGroupSlice.utils';

interface AdcmHostProviderConfigGroupActionsState {
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

type HostProviderConfigGroupPayload = {
  hostProviderId: number;
  configGroupId: number;
};

const deleteHostProviderConfigGroup = createAsyncThunk(
  'adcm/hostproviderConfigGroupActions/deleteConfigGroup',
  async ({ hostProviderId, configGroupId }: HostProviderConfigGroupPayload, thunkAPI) => {
    try {
      await AdcmHostProviderConfigGroupsApi.deleteConfigGroup(hostProviderId, configGroupId);

      thunkAPI.dispatch(showSuccess({ message: 'Config Group was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteHostProviderConfigGroupWithUpdate = createAsyncThunk(
  'adcm/hostproviderConfigGroupActions/deleteConfigGroupWithUpdate',
  async (arg: HostProviderConfigGroupPayload, thunkAPI) => {
    await thunkAPI.dispatch(deleteHostProviderConfigGroup(arg)).unwrap();
    thunkAPI.dispatch(getHostProviderConfigGroups(arg.hostProviderId));
  },
);

type CreateHostProviderConfigGroupPayload = {
  hostProviderId: number;
  data: AdcmHostProviderConfigGroupCreateData;
};

const createHostProviderConfigGroup = createAsyncThunk(
  'adcm/hostproviderConfigGroupActions/createConfigGroup',
  async ({ hostProviderId, data }: CreateHostProviderConfigGroupPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsCreating(true));
      return await AdcmHostProviderConfigGroupsApi.createConfigGroup(hostProviderId, data);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsCreating(false));
    }
  },
);

const getHostProviderConfigGroupHostsCandidates = createAsyncThunk(
  'adcm/hostproviderConfigGroupActions/getConfigGroupHostsCandidates',
  async ({ hostProviderId, configGroupId }: HostProviderConfigGroupPayload, thunkAPI) => {
    try {
      return await AdcmHostProviderConfigGroupsApi.getConfigGroupHostsCandidates(hostProviderId, configGroupId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

type SaveHostProviderConfigGroupMappedHostsPayload = HostProviderConfigGroupPayload & {
  mappedHostsIds: number[];
};

const saveHostProviderConfigGroupMappedHosts = createAsyncThunk(
  'adcm/hostproviderConfigGroupActions/saveConfigGroupMappedHosts',
  async ({ hostProviderId, mappedHostsIds }: SaveHostProviderConfigGroupMappedHostsPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(setIsSaveMapping(true));

      const {
        adcm: {
          hostProviderConfigGroupActions: {
            mappingDialog: { configGroup },
          },
        },
      } = thunkAPI.getState();

      const isMappingFullSuccess = await mappedHostsToConfigGroup({
        configGroup,
        mappedHostsIds,
        appendHost: (configGroupId, hostId) =>
          AdcmHostProviderConfigGroupsApi.mappedHostToConfigGroup(hostProviderId, configGroupId, hostId),
        removeHost: (configGroupId, hostId) =>
          AdcmHostProviderConfigGroupsApi.unmappedHostToConfigGroup(hostProviderId, configGroupId, hostId),
        dispatch: thunkAPI.dispatch,
      });

      return thunkAPI.fulfillWithValue(isMappingFullSuccess);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(closeMappingDialog());
      thunkAPI.dispatch(getHostProviderConfigGroups(hostProviderId));
    }
  },
);

const createInitialState = (): AdcmHostProviderConfigGroupActionsState => ({
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

const hostProviderConfigGroupActionsSlice = createSlice({
  name: 'adcm/hostProviderConfigGroupActions',
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
      .addCase(createHostProviderConfigGroup.fulfilled, (state) => {
        hostProviderConfigGroupActionsSlice.caseReducers.closeCreateDialog(state);
      })
      .addCase(deleteHostProviderConfigGroupWithUpdate.pending, (state) => {
        hostProviderConfigGroupActionsSlice.caseReducers.closeDeleteDialog(state);
      })
      .addCase(getHostProviderConfigGroupHostsCandidates.fulfilled, (state, action) => {
        state.relatedData.candidatesHosts = action.payload;
      })
      .addCase(getHostProviderConfigGroupHostsCandidates.rejected, (state) => {
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
} = hostProviderConfigGroupActionsSlice.actions;

export {
  cleanupActions,
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  openMappingDialog,
  closeMappingDialog,
};
export default hostProviderConfigGroupActionsSlice.reducer;

export {
  createHostProviderConfigGroup,
  deleteHostProviderConfigGroupWithUpdate,
  getHostProviderConfigGroupHostsCandidates,
  saveHostProviderConfigGroupMappedHosts,
};
