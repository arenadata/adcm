import { createSlice } from '@reduxjs/toolkit';
import type { PayloadAction } from '@reduxjs/toolkit';

export type ClustersViewMode = 'table' | 'widget';

type ClustersViewState = {
  viewMode: ClustersViewMode;
  selectedClusterId: number | null;
};

const createInitialState = (): ClustersViewState => ({
  viewMode: 'table',
  selectedClusterId: null,
});

const clustersViewSlice = createSlice({
  name: 'adcm/clustersView',
  initialState: createInitialState(),
  reducers: {
    setViewMode(state, action: PayloadAction<ClustersViewMode>) {
      state.viewMode = action.payload;
      if (action.payload === 'table') {
        state.selectedClusterId = null;
      }
    },
    setSelectedClusterId(state, action: PayloadAction<number | null>) {
      state.selectedClusterId = action.payload;
    },
    cleanupClustersView(state) {
      state.selectedClusterId = null;
    },
  },
});

export const { setViewMode, setSelectedClusterId, cleanupClustersView } = clustersViewSlice.actions;
export default clustersViewSlice.reducer;
