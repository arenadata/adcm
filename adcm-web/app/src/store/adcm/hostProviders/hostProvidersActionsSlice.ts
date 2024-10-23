import { createAsyncThunk } from '@store/redux';
import { AdcmHostProvidersApi, AdcmPrototypesApi, RequestError } from '@api';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getHostProviders } from './hostProvidersSlice';
import { AdcmHostProvider, AdcmHostProviderPayload, AdcmPrototypeType, AdcmPrototypeVersions } from '@models/adcm';
import { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

interface AdcmHostProvidersActionsState extends ModalState<AdcmHostProvider, 'hostprovider'> {
  createDialog: {
    isOpen: boolean;
  };
  deleteDialog: {
    hostprovider: AdcmHostProvider | null;
  };
  relatedData: {
    prototypeVersions: AdcmPrototypeVersions[];
    isRelatedDataLoaded: boolean;
  };
}

type CreateAdcmHostproviderWithLicensePayload = AdcmHostProviderPayload & {
  isNeededLicenseAcceptance: boolean;
};

const createHostProviderWithUpdate = createAsyncThunk(
  'adcm/hostProviders/createHostProviderDialog/createHostProviderWithUpdate',
  async ({ isNeededLicenseAcceptance, ...arg }: CreateAdcmHostproviderWithLicensePayload, thunkAPI) => {
    try {
      if (isNeededLicenseAcceptance) {
        await AdcmPrototypesApi.postAcceptLicense(arg.prototypeId);
      }
      await AdcmHostProvidersApi.postHostProviders(arg);
      await thunkAPI.dispatch(getHostProviders());
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteHostProviderWithUpdate = createAsyncThunk(
  'adcm/hostProvidersActions/deleteHostProvider',
  async (deletableId: number, thunkAPI) => {
    try {
      await AdcmHostProvidersApi.deleteHostProvider(deletableId);
      await thunkAPI.dispatch(getHostProviders());
      thunkAPI.dispatch(showSuccess({ message: 'Hostprovider was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
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

const createInitialState = (): AdcmHostProvidersActionsState => ({
  createDialog: {
    isOpen: false,
  },
  updateDialog: {
    hostprovider: null,
  },
  deleteDialog: {
    hostprovider: null,
  },
  relatedData: {
    prototypeVersions: [],
    isRelatedDataLoaded: false,
  },
});

const hostProvidersActionsSlice = createCrudSlice({
  name: 'adcm/hostProvidersActions',
  entityName: 'hostprovider',
  createInitialState,
  reducers: {
    cleanupHostProvidersActions() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(createHostProviderWithUpdate.pending, (state) => {
      hostProvidersActionsSlice.caseReducers.closeCreateDialog(state);
    });
    builder.addCase(deleteHostProviderWithUpdate.pending, (state) => {
      hostProvidersActionsSlice.caseReducers.closeDeleteDialog(state);
    });
    builder.addCase(loadPrototypeVersions.fulfilled, (state, action) => {
      state.relatedData.prototypeVersions = action.payload;
      state.relatedData.isRelatedDataLoaded = true;
    });
    builder.addCase(loadPrototypeVersions.rejected, (state) => {
      state.relatedData.prototypeVersions = [];
      state.relatedData.isRelatedDataLoaded = false;
    });
  },
});

const { openDeleteDialog, closeDeleteDialog, openCreateDialog, closeCreateDialog } = hostProvidersActionsSlice.actions;
export {
  openDeleteDialog,
  closeDeleteDialog,
  openCreateDialog,
  closeCreateDialog,
  createHostProviderWithUpdate as createHostProvider,
  deleteHostProviderWithUpdate as deleteHostProvider,
  loadRelatedData,
};

export default hostProvidersActionsSlice.reducer;
