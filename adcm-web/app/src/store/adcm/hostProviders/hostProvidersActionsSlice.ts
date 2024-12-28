import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { AdcmHostProvidersApi, AdcmPrototypesApi } from '@api';
import { showError, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getHostProviders } from './hostProvidersSlice';
import type { AdcmHostProvider, AdcmHostProviderPayload, AdcmPrototypeVersions } from '@models/adcm';
import { AdcmPrototypeType } from '@models/adcm';
import type { ModalState } from '@models/modal';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';

interface AdcmHostProvidersActionsState extends ModalState<AdcmHostProvider, 'hostprovider'> {
  createDialog: {
    isOpen: boolean;
    isCreating: boolean;
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
      thunkAPI.dispatch(setIsCreating(true));
      if (isNeededLicenseAcceptance) {
        await AdcmPrototypesApi.postAcceptLicense(arg.prototypeId);
      }
      await AdcmHostProvidersApi.postHostProviders(arg);
      await thunkAPI.dispatch(getHostProviders());
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setIsCreating(false));
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
  async (_arg, thunkAPI) => {
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
  async (_arg, thunkAPI) => {
    await thunkAPI.dispatch(loadPrototypeVersions());
  },
);

const createInitialState = (): AdcmHostProvidersActionsState => ({
  createDialog: {
    isOpen: false,
    isCreating: false,
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
    setIsCreating(state, action) {
      state.createDialog.isCreating = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(createHostProviderWithUpdate.fulfilled, (state) => {
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

const { openDeleteDialog, closeDeleteDialog, openCreateDialog, closeCreateDialog, setIsCreating } =
  hostProvidersActionsSlice.actions;
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
