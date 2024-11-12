import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import type { AdcmConfigGroup } from '@models/adcm';
import { AdcmClusterServiceComponentConfigGroupsApi } from '@api';

interface GetServiceComponentConfigGroupPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
  configGroupId: number;
}

const getServiceComponentConfigGroup = createAsyncThunk(
  'adcm/serviceComponent/configGroup/getServiceComponentConfigGroup',
  async ({ clusterId, serviceId, componentId, configGroupId }: GetServiceComponentConfigGroupPayload) => {
    return await AdcmClusterServiceComponentConfigGroupsApi.getConfigGroup(
      clusterId,
      serviceId,
      componentId,
      configGroupId,
    );
  },
);

interface AdcmServiceComponentConfigGroupState {
  serviceComponentConfigGroup: AdcmConfigGroup | null;
  isLoading: boolean;
}

const createInitialState = (): AdcmServiceComponentConfigGroupState => ({
  serviceComponentConfigGroup: null,
  isLoading: true,
});

const serviceComponentConfigGroupSingle = createSlice({
  name: 'adcm/serviceComponent/configGroup',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupServiceComponentConfigGroup() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getServiceComponentConfigGroup.fulfilled, (state, action) => {
      state.serviceComponentConfigGroup = action.payload;
    });
    builder.addCase(getServiceComponentConfigGroup.rejected, (state) => {
      state.serviceComponentConfigGroup = null;
    });
  },
});

const { cleanupServiceComponentConfigGroup } = serviceComponentConfigGroupSingle.actions;
export { getServiceComponentConfigGroup, cleanupServiceComponentConfigGroup };
export default serviceComponentConfigGroupSingle.reducer;
