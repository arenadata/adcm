import { AdcmBundlesApi, AdcmPrototypesApi, RequestError } from '@api';
import { defaultSpinnerDelay } from '@constants';
import { AdcmPrototype, AdcmPrototypeType } from '@models/adcm';
import { AdcmBundle } from '@models/adcm/bundle';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';

interface AdcmBundleState {
  bundle?: AdcmBundle;
  isLicenseLoading: boolean;
  relatedData: {
    prototype?: AdcmPrototype;
  };
}

interface AcceptBundleLicensePayload {
  bundleId: number;
  prototypeId: number;
}

const loadBundle = createAsyncThunk('adcm/bundle/loadBundle', async (bundleId: number, thunkAPI) => {
  try {
    const bundle = await AdcmBundlesApi.getBundle(bundleId);
    return bundle;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
  }
});

const loadRelatedPrototype = createAsyncThunk('adcm/bundle/loadPrototype', async (bundleId: number, thunkAPI) => {
  try {
    let prototype = await AdcmPrototypesApi.getPrototypes({ bundleId, type: AdcmPrototypeType.Cluster });
    if (!prototype.results.length) {
      prototype = await AdcmPrototypesApi.getPrototypes({ bundleId, type: AdcmPrototypeType.Provider });
    }
    return prototype.results;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
  }
});

const getRelatedPrototype = createAsyncThunk('adcm/bundle/getRelatedPrototype', async (arg: number, thunkAPI) => {
  thunkAPI.dispatch(setIsLicenseLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadRelatedPrototype(arg));

  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLicenseLoading(false));
    },
  });
});

const acceptBundleLicenseWithUpdate = createAsyncThunk(
  'adcm/bundle/acceptBundleLicense',
  async ({ bundleId, prototypeId }: AcceptBundleLicensePayload, thunkAPI) => {
    try {
      await AdcmPrototypesApi.postAcceptLicense(prototypeId);
      await thunkAPI.dispatch(loadRelatedPrototype(bundleId));
      thunkAPI.dispatch(showInfo({ message: 'The license has been accepted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    }
  },
);

const deleteBundle = createAsyncThunk('adcm/bundle/deleteBundle', async (bundleId: number, thunkAPI) => {
  try {
    await AdcmBundlesApi.deleteBundle(bundleId);
    thunkAPI.dispatch(showInfo({ message: 'The bundle has been deleted' }));
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
  }
});

const createInitialState = (): AdcmBundleState => ({
  bundle: undefined,
  relatedData: {
    prototype: undefined,
  },
  isLicenseLoading: false,
});

const bundleSlice = createSlice({
  name: 'adcm/bundle',
  initialState: createInitialState(),
  reducers: {
    setIsLicenseLoading(state, action) {
      state.isLicenseLoading = action.payload;
    },
    cleanupBundle() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadBundle.fulfilled, (state, action) => {
      state.bundle = action.payload;
    });
    builder.addCase(loadBundle.rejected, (state) => {
      state.bundle = undefined;
    });
    builder.addCase(loadRelatedPrototype.fulfilled, (state, action) => {
      state.relatedData.prototype = action.payload?.[0];
    });
    builder.addCase(loadRelatedPrototype.rejected, (state) => {
      state.relatedData.prototype = undefined;
    });
  },
});

const { cleanupBundle, setIsLicenseLoading } = bundleSlice.actions;
export {
  loadBundle,
  loadRelatedPrototype,
  acceptBundleLicenseWithUpdate,
  cleanupBundle,
  deleteBundle,
  getRelatedPrototype,
};
export default bundleSlice.reducer;
