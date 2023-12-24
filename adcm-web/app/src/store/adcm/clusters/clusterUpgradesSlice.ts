import { createSlice } from '@reduxjs/toolkit';
import { AdcmCluster, AdcmUpgradeDetails, AdcmUpgradeRunConfig, AdcmUpgradeShort } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { AdcmClustersApi, AdcmPrototypesApi, RequestError } from '@api';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

const acceptPrototypeLicense = createAsyncThunk(
  'adcm/clusterUpgrades/acceptServiceLicense',
  async (servicePrototypeId: number, thunkAPI) => {
    try {
      await AdcmPrototypesApi.postAcceptLicense(servicePrototypeId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const loadClusterUpgrades = createAsyncThunk(
  'adcm/clusterUpgrades/loadClusterUpgrades',
  async (clusterId: number, thunkAPI) => {
    try {
      return await AdcmClustersApi.getClusterUpgrades(clusterId);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

type LoadAdcmClusterUpgradeDetailsPayload = {
  clusterId: number;
  upgradeId: number;
};

const loadClusterUpgradeDetails = createAsyncThunk(
  'adcm/clustersActions/loadClusterUpgradeDetails',
  async ({ clusterId, upgradeId }: LoadAdcmClusterUpgradeDetailsPayload, thunkAPI) => {
    try {
      return await AdcmClustersApi.getClusterUpgrade(clusterId, upgradeId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface RunClusterUpgradesPayload {
  cluster: AdcmCluster;
  upgradeId: number;
  upgradeRunConfig: AdcmUpgradeRunConfig;
}

const runClusterUpgrade = createAsyncThunk(
  'adcm/clusterUpgrades/runClusterUpgrade',
  async ({ cluster, upgradeId, upgradeRunConfig }: RunClusterUpgradesPayload, thunkAPI) => {
    try {
      await AdcmClustersApi.runClusterUpgrade(cluster.id, upgradeId, upgradeRunConfig);

      thunkAPI.dispatch(showInfo({ message: 'Upgrade was running successfully' }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmClusterUpgradesState = {
  dialog: {
    cluster: AdcmCluster | null;
  };
  relatedData: {
    // (upgradeId => UpgradeDetails)
    upgradesDetails: Record<AdcmUpgradeShort['id'], AdcmUpgradeDetails>;
    upgradesList: AdcmUpgradeShort[];
  };
};

const createInitialState = (): AdcmClusterUpgradesState => ({
  dialog: {
    cluster: null,
  },
  relatedData: {
    upgradesDetails: {},
    upgradesList: [],
  },
});

const clusterUpgradesSlice = createSlice({
  name: 'adcm/clusterUpgrades',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterUpgrades() {
      return createInitialState();
    },
    openClusterUpgradeDialog(state, action) {
      state.dialog.cluster = action.payload;
    },
    closeClusterUpgradeDialog() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterUpgrades.fulfilled, (state, action) => {
      state.relatedData.upgradesList = action.payload;
    });
    builder.addCase(loadClusterUpgrades.rejected, (state) => {
      state.relatedData.upgradesList = [];
    });
    builder.addCase(loadClusterUpgradeDetails.fulfilled, (state, action) => {
      const { upgradeId } = action.meta.arg;
      state.relatedData.upgradesDetails[upgradeId] = action.payload;
    });
    builder.addCase(runClusterUpgrade.pending, () => {
      clusterUpgradesSlice.caseReducers.closeClusterUpgradeDialog();
    });
  },
});

export const { cleanupClusterUpgrades, openClusterUpgradeDialog, closeClusterUpgradeDialog } =
  clusterUpgradesSlice.actions;
export { loadClusterUpgrades, loadClusterUpgradeDetails, runClusterUpgrade, acceptPrototypeLicense };

export default clusterUpgradesSlice.reducer;
