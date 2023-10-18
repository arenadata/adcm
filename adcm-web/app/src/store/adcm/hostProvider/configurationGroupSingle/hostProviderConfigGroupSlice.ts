import { AdcmHostProviderConfigGroupsApi } from '@api';
import { AdcmConfigGroup } from '@models/adcm';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';

type GetHostProviderConfigGroupPayload = {
  hostProviderId: number;
  configGroupId: number;
};

const getHostProviderConfigGroup = createAsyncThunk(
  'adcm/hostProviderConfigGroup/getHostProviderConfigGroup',
  async ({ hostProviderId, configGroupId }: GetHostProviderConfigGroupPayload) => {
    return await AdcmHostProviderConfigGroupsApi.getConfigGroup(hostProviderId, configGroupId);
  },
);

type AdcmHostProviderConfigGroupState = {
  hostProviderConfigGroup: AdcmConfigGroup | null;
  isLoading: boolean;
};

const createInitialState = (): AdcmHostProviderConfigGroupState => ({
  hostProviderConfigGroup: null,
  isLoading: false,
});

const hostProviderConfigGroupSlice = createSlice({
  name: 'adcm/hostProviderConfigGroup',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupHostProviderConfigGroup() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(getHostProviderConfigGroup.fulfilled, (state, action) => {
      state.hostProviderConfigGroup = action.payload;
    });
    builder.addCase(getHostProviderConfigGroup.rejected, (state) => {
      state.hostProviderConfigGroup = null;
    });
  },
});

const { cleanupHostProviderConfigGroup } = hostProviderConfigGroupSlice.actions;
export { getHostProviderConfigGroup, cleanupHostProviderConfigGroup };
export default hostProviderConfigGroupSlice.reducer;
