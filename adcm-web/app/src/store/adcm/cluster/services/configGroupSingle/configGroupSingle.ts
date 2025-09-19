import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import type { AdcmConfigGroup } from '@models/adcm';
import { AdcmClusterServiceConfigGroupsApi } from '@api';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

interface GetClusterServiceConfigGroupPayload {
  clusterId: number;
  serviceId: number;
  configGroupId: number;
}

const getClusterServiceConfigGroup = createAsyncThunk(
  'adcm/cluster/services/serviceConfigGroup/getClusterServiceConfigGroup',
  async ({ clusterId, serviceId, configGroupId }: GetClusterServiceConfigGroupPayload) => {
    return await AdcmClusterServiceConfigGroupsApi.getConfigGroup(clusterId, serviceId, configGroupId);
  },
);

interface AdcmClusterServiceConfigGroupState {
  serviceConfigGroup: AdcmConfigGroup | null;
  isLoading: boolean;
}

const createInitialState = (): AdcmClusterServiceConfigGroupState => ({
  serviceConfigGroup: null,
  isLoading: true,
});

const serviceConfigGroupSlice = createSlice({
  name: 'adcm/cluster/services/serviceConfigGroup',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterServiceConfigGroup() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getClusterServiceConfigGroup.fulfilled, (state, action) => {
      state.serviceConfigGroup = action.payload;
    });
    builder.addCase(getClusterServiceConfigGroup.rejected, (state) => {
      state.serviceConfigGroup = null;
    });
    builder.addCase(wsActions['update_config-group'], (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.serviceConfigGroup?.id === id) {
        state.serviceConfigGroup = { ...state.serviceConfigGroup, ...changes };
      }
    });
  },
});

const { cleanupClusterServiceConfigGroup } = serviceConfigGroupSlice.actions;
export { getClusterServiceConfigGroup, cleanupClusterServiceConfigGroup };
export default serviceConfigGroupSlice.reducer;
