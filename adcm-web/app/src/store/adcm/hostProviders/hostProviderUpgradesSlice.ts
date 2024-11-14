import { createSlice } from '@reduxjs/toolkit';
import type { AdcmHostProvider, AdcmUpgradeDetails, AdcmUpgradeRunConfig, AdcmUpgradeShort } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmHostProvidersApi, AdcmPrototypesApi } from '@api';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

const acceptPrototypeLicense = createAsyncThunk(
  'adcm/hostProviderUpgrades/acceptPrototypeLicense',
  async (prototypeId: number, thunkAPI) => {
    try {
      await AdcmPrototypesApi.postAcceptLicense(prototypeId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const loadHostProviderUpgrades = createAsyncThunk(
  'adcm/hostProviderUpgrades/loadHostProviderUpgrades',
  async (hostProviderId: number, thunkAPI) => {
    try {
      return await AdcmHostProvidersApi.getHostProviderUpgrades(hostProviderId);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

type LoadAdcmHostProviderUpgradeDetailsPayload = {
  hostProviderId: number;
  upgradeId: number;
};

const loadHostProviderUpgradeDetails = createAsyncThunk(
  'adcm/hostProvidersActions/loadHostProviderUpgradeDetails',
  async ({ hostProviderId, upgradeId }: LoadAdcmHostProviderUpgradeDetailsPayload, thunkAPI) => {
    try {
      return await AdcmHostProvidersApi.getHostProviderUpgrade(hostProviderId, upgradeId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface RunHostProviderUpgradesPayload {
  hostProvider: AdcmHostProvider;
  upgradeId: number;
  upgradeRunConfig: AdcmUpgradeRunConfig;
}

const runHostProviderUpgrade = createAsyncThunk(
  'adcm/hostProviderUpgrades/runHostProviderUpgrade',
  async ({ hostProvider, upgradeId, upgradeRunConfig }: RunHostProviderUpgradesPayload, thunkAPI) => {
    try {
      await AdcmHostProvidersApi.runHostProviderUpgrade(hostProvider.id, upgradeId, upgradeRunConfig);

      thunkAPI.dispatch(showSuccess({ message: 'Upgrade was running successfully' }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmHostProviderUpgradesState = {
  dialog: {
    hostProvider: AdcmHostProvider | null;
  };
  relatedData: {
    // (upgradeId => UpgradeDetails)
    upgradesDetails: Record<AdcmUpgradeShort['id'], AdcmUpgradeDetails>;
    upgradesList: AdcmUpgradeShort[];
  };
};

const createInitialState = (): AdcmHostProviderUpgradesState => ({
  dialog: {
    hostProvider: null,
  },
  relatedData: {
    upgradesDetails: {},
    upgradesList: [],
  },
});

const hostProviderUpgradesSlice = createSlice({
  name: 'adcm/hostProviderUpgrades',
  initialState: createInitialState(),
  reducers: {
    cleanupHostProviderUpgrades() {
      return createInitialState();
    },
    opeHostProviderUpgradeDialog(state, action) {
      state.dialog.hostProvider = action.payload;
    },
    closeHostProviderUpgradeDialog() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHostProviderUpgrades.fulfilled, (state, action) => {
      state.relatedData.upgradesList = action.payload;
    });
    builder.addCase(loadHostProviderUpgrades.rejected, (state) => {
      state.relatedData.upgradesList = [];
    });
    builder.addCase(loadHostProviderUpgradeDetails.fulfilled, (state, action) => {
      const { upgradeId } = action.meta.arg;
      state.relatedData.upgradesDetails[upgradeId] = action.payload;
    });
    builder.addCase(runHostProviderUpgrade.pending, () => {
      hostProviderUpgradesSlice.caseReducers.closeHostProviderUpgradeDialog();
    });
  },
});

export const { cleanupHostProviderUpgrades, opeHostProviderUpgradeDialog, closeHostProviderUpgradeDialog } =
  hostProviderUpgradesSlice.actions;
export { loadHostProviderUpgrades, loadHostProviderUpgradeDetails, runHostProviderUpgrade, acceptPrototypeLicense };

export default hostProviderUpgradesSlice.reducer;
