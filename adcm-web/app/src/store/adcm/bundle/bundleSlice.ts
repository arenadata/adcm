import { AdcmBundlesApi, AdcmPrototypesApi, RequestError } from '@api';
import { defaultSpinnerDelay } from '@constants';
import { AdcmBundle } from '@models/adcm/bundle';
import { LoadState } from '@models/loadState';
import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';

interface AdcmBundleState {
  bundle?: AdcmBundle;
  licenseLoadState: LoadState;
}

interface AcceptBundleLicensePayload {
  bundleId: number;
  prototypeId: number;
}

const loadBundleFromBackend = createAsyncThunk('adcm/bundle/loadBundle', async (bundleId: number, thunkAPI) => {
  try {
    const bundle = await AdcmBundlesApi.getBundle(bundleId);
    return bundle;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: 'Bundle not found' }));
  }
});

const getBundle = createAsyncThunk('adcm/bundle/getBundle', async (arg: number, thunkAPI) => {
  thunkAPI.dispatch(setLicenseLoadState(LoadState.Loading));
  const startDate = new Date();

  await thunkAPI.dispatch(loadBundleFromBackend(arg));

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setLicenseLoadState(LoadState.Loaded));
    },
  });
});

const acceptBundleLicense = createAsyncThunk(
  'adcm/bundle/acceptBundleLicense',
  async (prototypeId: number, thunkAPI) => {
    try {
      await AdcmPrototypesApi.postAcceptLicense(prototypeId);
      thunkAPI.dispatch(showSuccess({ message: 'The license has been accepted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const acceptBundleLicenseWithUpdate = createAsyncThunk(
  'adcm/bundle/acceptBundleLicenseWithUpdate',
  async ({ bundleId, prototypeId }: AcceptBundleLicensePayload, thunkAPI) => {
    await thunkAPI.dispatch(acceptBundleLicense(prototypeId)).unwrap();
    thunkAPI.dispatch(loadBundleFromBackend(bundleId));
  },
);

const deleteBundle = createAsyncThunk('adcm/bundle/deleteBundle', async (bundleId: number, thunkAPI) => {
  try {
    await AdcmBundlesApi.deleteBundle(bundleId);
    thunkAPI.dispatch(showSuccess({ message: 'The bundle has been deleted' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
  }
});

const createInitialState = (): AdcmBundleState => ({
  bundle: undefined,
  licenseLoadState: LoadState.NotLoaded,
});

const bundleSlice = createSlice({
  name: 'adcm/bundle',
  initialState: createInitialState(),
  reducers: {
    setLicenseLoadState(state, action) {
      state.licenseLoadState = action.payload;
    },
    cleanupBundle() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadBundleFromBackend.fulfilled, (state, action) => {
      state.bundle = action.payload;
    });
    builder.addCase(loadBundleFromBackend.rejected, (state) => {
      state.bundle = undefined;
    });
  },
});

const { cleanupBundle, setLicenseLoadState } = bundleSlice.actions;
export { getBundle, acceptBundleLicenseWithUpdate, cleanupBundle, deleteBundle, setLicenseLoadState };
export default bundleSlice.reducer;
