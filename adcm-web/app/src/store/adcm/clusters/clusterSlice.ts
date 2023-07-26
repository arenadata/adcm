import { AdcmClustersApi } from '@api';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmCluster } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';

interface AdcmClusterState {
  cluster: AdcmCluster | undefined;
  isLoading: boolean;
}

const loadClusterFromBackend = createAsyncThunk(
  'adcm/clusters/loadClusterFromBackend',
  async (arg: number, thunkAPI) => {
    try {
      const cluster = await AdcmClustersApi.getCluster(arg);
      return cluster;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getCluster = createAsyncThunk('adcm/clusters/getCluster', async (arg: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadClusterFromBackend(arg));
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,

    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const createInitialState = (): AdcmClusterState => ({
  cluster: undefined,
  isLoading: false,
});

const clusterSlice = createSlice({
  name: 'adcm/cluster',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupCluster() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterFromBackend.fulfilled, (state, action) => {
      state.cluster = action.payload;
    });
    builder.addCase(loadClusterFromBackend.rejected, (state) => {
      state.cluster = undefined;
    });
  },
});

const { setIsLoading, cleanupCluster } = clusterSlice.actions;
export { getCluster, cleanupCluster };
export default clusterSlice.reducer;
