import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import {
  AdcmClusterConfigGroupsApi,
  AdcmClusterServiceConfigGroupsApi,
  AdcmClusterServiceComponentConfigGroupsApi,
  AdcmHostProviderConfigGroupsApi,
} from '@api';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getClusterConfigGroups } from '@store/adcm/cluster/configGroups/clusterConfigGroupsSlice';
import { getClusterServiceConfigGroups } from '@store/adcm/cluster/services/configGroups/serviceConfigGroupsSlice';
import { getServiceComponentConfigGroups } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsSlice';
import { getHostProviderConfigGroups } from '@store/adcm/hostProvider/configurationGroups/hostProviderConfigGroupsSlice';
import { getClusterConfigGroup } from '@store/adcm/cluster/configGroupSingle/clusterConfigGroup';
import { getClusterServiceConfigGroup } from '@store/adcm/cluster/services/configGroupSingle/configGroupSingle';
import { getServiceComponentConfigGroup } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroupSingle/serviceComponentConfigGroupSingleSlice';
import { getHostProviderConfigGroup } from '@store/adcm/hostProvider/configurationGroupSingle/hostProviderConfigGroupSlice';
import type { AdcmConfigGroup } from '@models/adcm';
import type { AppDispatch } from '@store/store';
import type {
  ConfigGroupOwner,
  ConfigGroupEntityArgs,
  EntityDescriptionDialogState,
  ClusterConfigGroupArgs,
  ServiceConfigGroupArgs,
  ComponentConfigGroupArgs,
  HostProviderConfigGroupArgs,
} from './entityDescriptionDialog.types';

type EditConfigGroupPayload = {
  entityType: ConfigGroupOwner;
  entityArgs: ConfigGroupEntityArgs;
  configGroupId: number;
  description: string;
};

async function patchConfigGroupDescription(payload: EditConfigGroupPayload, dispatch: AppDispatch): Promise<void> {
  const { entityType, entityArgs, configGroupId, description: descriptionRaw } = payload;
  const description = descriptionRaw.trim();
  switch (entityType) {
    case 'cluster': {
      const args = entityArgs as ClusterConfigGroupArgs;
      await AdcmClusterConfigGroupsApi.patchConfigGroupDescription(args.clusterId, configGroupId, description);
      dispatch(getClusterConfigGroups(args.clusterId));
      dispatch(getClusterConfigGroup({ clusterId: args.clusterId, configGroupId }));
      break;
    }
    case 'service': {
      const args = entityArgs as ServiceConfigGroupArgs;
      await AdcmClusterServiceConfigGroupsApi.patchConfigGroupDescription(
        args.clusterId,
        args.serviceId,
        configGroupId,
        description,
      );
      dispatch(getClusterServiceConfigGroups(args));
      dispatch(getClusterServiceConfigGroup({ ...args, configGroupId }));
      break;
    }
    case 'component': {
      const args = entityArgs as ComponentConfigGroupArgs;
      await AdcmClusterServiceComponentConfigGroupsApi.patchConfigGroupDescription(
        args.clusterId,
        args.serviceId,
        args.componentId,
        configGroupId,
        description,
      );
      dispatch(getServiceComponentConfigGroups(args));
      dispatch(getServiceComponentConfigGroup({ ...args, configGroupId }));
      break;
    }
    case 'hostprovider': {
      const args = entityArgs as HostProviderConfigGroupArgs;
      await AdcmHostProviderConfigGroupsApi.patchConfigGroupDescription(
        args.hostProviderId,
        configGroupId,
        description,
      );
      dispatch(getHostProviderConfigGroups(args.hostProviderId));
      dispatch(getHostProviderConfigGroup({ hostProviderId: args.hostProviderId, configGroupId }));
      break;
    }
  }
}

const editConfigGroupDescription = createAsyncThunk<EditConfigGroupPayload, EditConfigGroupPayload>(
  'adcm/entityDescriptionDialog/editConfigGroupDescription',
  async (payload, thunkAPI) => {
    try {
      await patchConfigGroupDescription(payload, thunkAPI.dispatch);
      thunkAPI.dispatch(showSuccess({ message: 'Configuration group description updated' }));
      return payload;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const closedState: EntityDescriptionDialogState = {
  configGroup: null,
  entityType: null,
  entityArgs: null,
};

const entityDescriptionDialogSlice = createSlice({
  name: 'adcm/entityDescriptionDialog',
  initialState: closedState,
  reducers: {
    openConfigGroupDescriptionDialog(
      _state,
      action: {
        payload: {
          configGroup: AdcmConfigGroup;
          entityType: ConfigGroupOwner;
          entityArgs: ConfigGroupEntityArgs;
        };
      },
    ): EntityDescriptionDialogState {
      return {
        configGroup: action.payload.configGroup,
        entityType: action.payload.entityType,
        entityArgs: action.payload.entityArgs,
      };
    },
    closeEntityDescriptionDialog(): EntityDescriptionDialogState {
      return closedState;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(editConfigGroupDescription.fulfilled, () => closedState);
  },
});

export const { openConfigGroupDescriptionDialog, closeEntityDescriptionDialog } = entityDescriptionDialogSlice.actions;
export { editConfigGroupDescription };
export default entityDescriptionDialogSlice.reducer;
