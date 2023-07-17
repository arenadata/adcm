import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { CreateAdcmClusterPayload, AdcmPrototypeVersions, PrototypeType } from '@models/adcm';
import { AdcmClustersApi, AdcmPrototypesApi } from '@api';
import { refreshClusters } from '../clustersSlice';

type AdcmClustersState = {
  isOpen: boolean;
  relatedData: {
    prototypeVersions: AdcmPrototypeVersions[];
    isLoaded: boolean;
  };
};

const createInitialState = (): AdcmClustersState => ({
  isOpen: false,
  relatedData: {
    prototypeVersions: [],
    isLoaded: false,
  },
});

const createCluster = createAsyncThunk(
  'adcm/clusters/createClusterDialog/createCluster',
  async (arg: CreateAdcmClusterPayload, thunkAPI) => {
    try {
      if (!arg.isLicenseAccepted) {
        await AdcmPrototypesApi.postAcceptLicense(arg.prototypeId);
      }

      const cluster = await AdcmClustersApi.postCluster(arg);
      return cluster;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(refreshClusters());
    }
  },
);

const loadPrototypeVersions = createAsyncThunk(
  'adcm/clusters/createClusterDialog/loadPrototypeVersions',
  async (arg, thunkAPI) => {
    try {
      const prototypeVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: PrototypeType.Cluster });
      return prototypeVersions;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadRelatedData = createAsyncThunk('adcm/clusters/createClusterDialog/loadRelatedData', async (arg, thunkAPI) => {
  await thunkAPI.dispatch(loadPrototypeVersions());
});

const open = createAsyncThunk('adcm/clusters/createClusterDialog/open', async (arg, thunkAPI) => {
  try {
    thunkAPI.dispatch(loadRelatedData());
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createClusterDialogSlice = createSlice({
  name: 'adcm/clusters/createClusterDialog',
  initialState: createInitialState(),
  reducers: {
    close() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(open.fulfilled, (state) => {
      state.isOpen = true;
    });
    builder.addCase(loadRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.prototypeVersions = action.payload;
    });
    builder.addCase(createCluster.fulfilled, () => {
      return createInitialState();
    });
  },
});

const { close } = createClusterDialogSlice.actions;
export { open, close, createCluster };
export default createClusterDialogSlice.reducer;
