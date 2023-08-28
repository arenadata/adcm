import { AdcmClustersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { refreshClusters } from './clustersSlice';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { createSlice } from '@reduxjs/toolkit';

interface AdcmClusterActionsState {
  deletableId: {
    id: number | null;
  };
}

const deleteClusterWithUpdate = createAsyncThunk(
  'adcm/clusters/clustersActions/removeCluster',
  async (clusterId: number, thunkAPI) => {
    try {
      await AdcmClustersApi.deleteCluster(clusterId);
      await thunkAPI.dispatch(refreshClusters());
      thunkAPI.dispatch(showInfo({ message: 'The cluster has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const createInitialState = (): AdcmClusterActionsState => ({
  deletableId: {
    id: null,
  },
});

const clustersActionsSlice = createSlice({
  name: 'adcm/clusters/clustersActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    openClusterDeleteDialog(state, action) {
      state.deletableId.id = action.payload;
    },
    closeClusterDeleteDialog(state) {
      state.deletableId.id = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(deleteClusterWithUpdate.pending, (state) => {
      clustersActionsSlice.caseReducers.closeClusterDeleteDialog(state);
    });
  },
});

const { openClusterDeleteDialog, closeClusterDeleteDialog } = clustersActionsSlice.actions;
export { deleteClusterWithUpdate, openClusterDeleteDialog, closeClusterDeleteDialog };
export default clustersActionsSlice.reducer;
