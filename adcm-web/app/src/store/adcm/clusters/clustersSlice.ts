import { createSlice } from '@reduxjs/toolkit';
import { AdcmClustersApi, RequestError } from '@api';
import { createAsyncThunk } from '@store/redux';
import { AdcmCluster } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

type AdcmClustersState = {
  clusters: AdcmCluster[];
  totalCount: number;
  itemsForActions: {
    deletableId: number | null;
  };
  isLoading: boolean;
};

const loadClustersFromBackend = createAsyncThunk('adcm/clusters/loadClustersFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      clustersTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmClustersApi.getClusters(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getClusters = createAsyncThunk('adcm/clusters/getClusters', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadClustersFromBackend());
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshClusters = createAsyncThunk('adcm/clusters/refreshClusters', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadClustersFromBackend());
});

const deleteClusterWithUpdate = createAsyncThunk('adcm/clusters/removeCluster', async (clusterId: number, thunkAPI) => {
  try {
    await AdcmClustersApi.deleteCluster(clusterId);
    await thunkAPI.dispatch(refreshClusters());
    thunkAPI.dispatch(showInfo({ message: 'The cluster has been removed' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return error;
  }
});

const createInitialState = (): AdcmClustersState => ({
  clusters: [],
  totalCount: 0,
  itemsForActions: {
    deletableId: null,
  },
  isLoading: false,
});

const clustersSlice = createSlice({
  name: 'adcm/clusters',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupClusters() {
      return createInitialState();
    },
    cleanupItemsForActions(state) {
      state.itemsForActions = createInitialState().itemsForActions;
    },
    setDeletableId(state, action) {
      state.itemsForActions.deletableId = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClustersFromBackend.fulfilled, (state, action) => {
      state.clusters = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClustersFromBackend.rejected, (state) => {
      state.clusters = [];
    });
    builder.addCase(deleteClusterWithUpdate.pending, (state) => {
      state.itemsForActions.deletableId = null;
    });
    builder.addCase(getClusters.pending, (state) => {
      clustersSlice.caseReducers.cleanupItemsForActions(state);
    });
  },
});

const { setIsLoading, cleanupClusters, setDeletableId } = clustersSlice.actions;
export { getClusters, refreshClusters, deleteClusterWithUpdate, cleanupClusters, setDeletableId };
export default clustersSlice.reducer;
