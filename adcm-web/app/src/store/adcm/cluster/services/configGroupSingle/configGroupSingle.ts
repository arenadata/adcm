import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import type { AdcmConfigGroup } from '@models/adcm';
import { AdcmClusterServiceConfigGroupsApi } from '@api';

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
  },
});

const { cleanupClusterServiceConfigGroup } = serviceConfigGroupSlice.actions;
export { getClusterServiceConfigGroup, cleanupClusterServiceConfigGroup };
export default serviceConfigGroupSlice.reducer;
