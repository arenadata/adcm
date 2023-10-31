import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { AdcmConfigGroup } from '@models/adcm';
import { AdcmClusterConfigGroupsApi } from '@api';

type GetClusterConfigGroupPayload = {
  clusterId: number;
  configGroupId: number;
};

const getClusterConfigGroup = createAsyncThunk(
  'adcm/clusterConfigGroup/getClusterConfigGroup',
  async ({ clusterId, configGroupId }: GetClusterConfigGroupPayload) => {
    return await AdcmClusterConfigGroupsApi.getConfigGroup(clusterId, configGroupId);
  },
);

type AdcmClusterConfigGroupState = {
  clusterConfigGroup: AdcmConfigGroup | null;
  isLoading: boolean;
};

const createInitialState = (): AdcmClusterConfigGroupState => ({
  clusterConfigGroup: null,
  isLoading: false,
});

const clusterConfigGroupSlice = createSlice({
  name: 'adcm/clusterConfigGroup',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusterConfigGroup() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getClusterConfigGroup.fulfilled, (state, action) => {
      state.clusterConfigGroup = action.payload;
    });
    builder.addCase(getClusterConfigGroup.rejected, (state) => {
      state.clusterConfigGroup = null;
    });
  },
});

const { cleanupClusterConfigGroup } = clusterConfigGroupSlice.actions;
export { getClusterConfigGroup, cleanupClusterConfigGroup };
export default clusterConfigGroupSlice.reducer;
