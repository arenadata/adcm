import { createSlice } from '@reduxjs/toolkit';
import { BreadcrumbsItemConfig } from '@routes/routes.types';

interface AdcmBreadcrumbsState {
  breadcrumbs: BreadcrumbsItemConfig[];
}

const createInitialState = (): AdcmBreadcrumbsState => ({
  breadcrumbs: [],
});

const breadcrumbsSlice = createSlice({
  name: 'adcm/breadcrumbs',
  initialState: createInitialState(),
  reducers: {
    cleanupBreadcrumbs() {
      return createInitialState();
    },
    setBreadcrumbs(state, action) {
      state.breadcrumbs = action.payload;
    },
  },
});

export const { cleanupBreadcrumbs, setBreadcrumbs } = breadcrumbsSlice.actions;
export default breadcrumbsSlice.reducer;
