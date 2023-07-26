import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmPrototypeType, AdcmPrototypeVersions, AdcmHostProviderPayload } from '@models/adcm';
import { AdcmHostProvidersApi, AdcmPrototypesApi } from '@api';
import { refreshHostProviders } from '../hostProvidersSlice';

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

const createHostProvider = createAsyncThunk(
  'adcm/hostProviders/createHostProviderDialog/createHostProvider',
  async (arg: AdcmHostProviderPayload, thunkAPI) => {
    try {
      await AdcmHostProvidersApi.postHostProviders(arg);
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(refreshHostProviders());
    }
  },
);

const loadPrototypeVersions = createAsyncThunk(
  'adcm/hostProviders/createHostProviderDialog/loadPrototypeVersions',
  async (arg, thunkAPI) => {
    try {
      const prototypeVersions = await AdcmPrototypesApi.getPrototypeVersions({ type: AdcmPrototypeType.Provider });
      return prototypeVersions;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadRelatedData = createAsyncThunk(
  'adcm/hostProviders/createHostProviderDialog/loadRelatedData',
  async (arg, thunkAPI) => {
    await thunkAPI.dispatch(loadPrototypeVersions());
  },
);

const open = createAsyncThunk('adcm/hostProviders/createHostProviderDialog/open', async (arg, thunkAPI) => {
  try {
    thunkAPI.dispatch(loadRelatedData());
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const createHostProviderDialogSlice = createSlice({
  name: 'adcm/hostProviders/createHostProviderDialog',
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
    builder.addCase(createHostProvider.fulfilled, () => {
      return createInitialState();
    });
  },
});

const { close } = createHostProviderDialogSlice.actions;
export { open, close, createHostProvider };
export default createHostProviderDialogSlice.reducer;
