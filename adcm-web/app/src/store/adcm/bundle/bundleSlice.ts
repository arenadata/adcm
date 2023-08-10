import { AdcmBundlesApi, AdcmPrototypesApi, RequestError } from '@api';
import { AdcmPrototype, AdcmPrototypeType } from '@models/adcm';
import { AdcmBundle } from '@models/adcm/bundle';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface AdcmBundleState {
  bundle?: AdcmBundle;
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
});

const bundleSlice = createSlice({
  name: 'adcm/bundle',
  initialState: createInitialState(),
  reducers: {
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

const { cleanupBundle } = bundleSlice.actions;
export { loadBundle, loadRelatedPrototype, acceptBundleLicenseWithUpdate, cleanupBundle, deleteBundle };
export default bundleSlice.reducer;
