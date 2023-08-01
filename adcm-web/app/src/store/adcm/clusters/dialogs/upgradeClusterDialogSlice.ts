import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmCluster, AdcmClusterUpgrade, AdcmClusterActionDetails } from '@models/adcm';
import { AdcmClustersApi } from '@api';

type AdcmUpgradeClusterDialogState = {
  isOpen: boolean;
  cluster: AdcmCluster | undefined;
  relatedData: {
    upgrades: AdcmClusterUpgrade[];
    isLoaded: boolean;
    upgradeActionDetails: AdcmClusterActionDetails | undefined;
  };
};

type OpenUpgradeClusterDialogArgs = {
  cluster: AdcmCluster;
};

type LoadAdcmClusterUpgradesArgs = {
  clusterId: number;
};

type LoadAdcmClusterUpgradeActionDetailsArgs = {
  clusterId: number;
  upgradeId: number;
};

const createInitialState = (): AdcmUpgradeClusterDialogState => ({
  isOpen: false,
  cluster: undefined,
  relatedData: {
    upgrades: [],
    isLoaded: false,
    upgradeActionDetails: undefined,
  },
});

const loadClusterUpgrades = createAsyncThunk(
  'adcm/clusters/upgradeClusterDialog/loadClusterUpgrades',
  async (arg: LoadAdcmClusterUpgradesArgs, thunkAPI) => {
    try {
      const upgrades = await AdcmClustersApi.getClusterUpgrades(arg.clusterId);
      return upgrades;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadClusterUpgradeActionDetails = createAsyncThunk(
  'adcm/clusters/upgradeClusterDialog/loadClusterUpgradeActionDetails',
  async (arg: LoadAdcmClusterUpgradeActionDetailsArgs, thunkAPI) => {
    try {
      const upgradeActionDetails = await AdcmClustersApi.getClusterUpgrade(arg.clusterId, arg.upgradeId);
      return upgradeActionDetails;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadRelatedData = createAsyncThunk(
  'adcm/clusters/upgradeClusterDialog/loadRelatedData',
  async (arg, thunkAPI) => {
    const {
      adcm: {
        upgradeClusterDialog: { cluster },
      },
    } = thunkAPI.getState();
    if (cluster) {
      await thunkAPI.dispatch(loadClusterUpgrades({ clusterId: cluster.id }));
    }
  },
);

const open = createAsyncThunk(
  'adcm/clusters/upgradeClusterDialog/open',
  async (arg: OpenUpgradeClusterDialogArgs, thunkAPI) => {
    try {
      thunkAPI.dispatch(loadRelatedData());
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createClusterDialogSlice = createSlice({
  name: 'adcm/clusters/upgradeClusterDialog',
  initialState: createInitialState(),
  reducers: {
    close() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(open.pending, (state, action) => {
      state.cluster = action.meta.arg.cluster;
    });
    builder.addCase(open.fulfilled, (state) => {
      state.isOpen = true;
    });
    builder.addCase(loadRelatedData.fulfilled, (state) => {
      state.relatedData.isLoaded = true;
    });
    builder.addCase(loadClusterUpgrades.fulfilled, (state, action) => {
      state.relatedData.upgrades = action.payload;
    });
    builder.addCase(loadClusterUpgradeActionDetails.fulfilled, (state, action) => {
      state.relatedData.upgradeActionDetails = action.payload;
    });
  },
});

const { close } = createClusterDialogSlice.actions;
export { open, close, loadClusterUpgradeActionDetails };
export default createClusterDialogSlice.reducer;
