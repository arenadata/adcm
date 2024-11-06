import { createAsyncThunk } from '@store/redux';
import { getServices, setServiceMaintenanceMode } from '@store/adcm/cluster/services/servicesSlice';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { AdcmMaintenanceMode, AdcmService, AdcmServicePrototype } from '@models/adcm';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { clearSolvedDependencies } from '@utils/dependsOnUtils';
import { createCrudSlice } from '@store/createCrudSlice/createCrudSlice';
import { ModalState } from '@models/modal';

interface AddClusterServicePayload {
  clusterId: number;
  servicesIds: number[];
}

interface DeleteClusterServicePayload {
  clusterId: number;
  serviceId: number;
}

interface toggleMaintenanceModePayload {
  serviceId: number;
  clusterId: number;
  maintenanceMode: AdcmMaintenanceMode;
}

const addServices = createAsyncThunk(
  'adcm/servicesActions/addServices',
  async ({ clusterId, servicesIds }: AddClusterServicePayload, thunkAPI) => {
    try {
      await AdcmClusterServicesApi.addClusterService(clusterId, servicesIds);

      const message = servicesIds.length > 1 ? 'All selected services have been added' : 'The service has been added';
      thunkAPI.dispatch(showSuccess({ message }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    } finally {
      thunkAPI.dispatch(setIsActionInProgress(false));
    }
  },
);

const addServicesWithUpdate = createAsyncThunk(
  'adcm/servicesActions/addServicesWithUpdate',
  async (arg: AddClusterServicePayload, thunkAPI) => {
    thunkAPI.dispatch(setIsActionInProgress(true));

    await thunkAPI.dispatch(addServices(arg)).unwrap();

    thunkAPI.dispatch(cleanupActions());
    await thunkAPI.dispatch(getServices({ clusterId: arg.clusterId })).unwrap();

    thunkAPI.dispatch(setIsActionInProgress(false));
  },
);

const deleteService = createAsyncThunk(
  'adcm/servicesActions/deleteService',
  async ({ clusterId, serviceId }: DeleteClusterServicePayload, thunkAPI) => {
    try {
      await AdcmClusterServicesApi.deleteClusterService(clusterId, serviceId);
      thunkAPI.dispatch(showSuccess({ message: 'Service was deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    } finally {
      thunkAPI.dispatch(getServices({ clusterId }));
    }
  },
);

const deleteServiceWithUpdate = createAsyncThunk(
  'adcm/servicesActions/deleteServiceWithUpdate',
  async (arg: DeleteClusterServicePayload, thunkAPI) => {
    await thunkAPI.dispatch(deleteService(arg)).unwrap();

    thunkAPI.dispatch(cleanupActions());
    await thunkAPI.dispatch(getServices({ clusterId: arg.clusterId })).unwrap();
  },
);

const getServiceCandidates = createAsyncThunk(
  'adcm/servicesActions/getServiceCandidates',
  async (clusterId: number, thunkAPI) => {
    const startDate = new Date();
    thunkAPI.dispatch(setIsServiceCandidatesLoading(true));

    try {
      return await AdcmClusterServicesApi.getClusterServiceCandidates(clusterId);
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      executeWithMinDelay({
        startDate,
        delay: defaultSpinnerDelay,
        callback: () => {
          thunkAPI.dispatch(setIsServiceCandidatesLoading(false));
        },
      });
    }
  },
);

const toggleMaintenanceMode = createAsyncThunk(
  'adcm/servicesActions/toggleMaintenanceMode',
  async ({ clusterId, serviceId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      const data = await AdcmClusterServicesApi.toggleMaintenanceMode(clusterId, serviceId, maintenanceMode);
      const maintenanceModeStatus = maintenanceMode === AdcmMaintenanceMode.Off ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
      thunkAPI.dispatch(setServiceMaintenanceMode({ serviceId, maintenanceMode }));
      return data;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

interface AdcmClusterServicesActionsState extends ModalState<AdcmService, 'service'> {
  createDialog: {
    isOpen: boolean;
  };
  deleteDialog: {
    service: AdcmService | null;
  };
  maintenanceModeDialog: {
    service: AdcmService | null;
  };
  relatedData: {
    serviceCandidates: AdcmServicePrototype[];
    isServiceCandidatesLoading: boolean;
  };
  isActionInProgress: boolean;
}

const createInitialState = (): AdcmClusterServicesActionsState => ({
  createDialog: {
    isOpen: false,
  },
  updateDialog: {
    service: null,
  },
  maintenanceModeDialog: {
    service: null,
  },
  deleteDialog: {
    service: null,
  },
  relatedData: {
    serviceCandidates: [],
    isServiceCandidatesLoading: false,
  },
  isActionInProgress: false,
});

const servicesActionsSlice = createCrudSlice({
  name: 'adcm/servicesActions',
  entityName: 'service',
  createInitialState,
  reducers: {
    setIsServiceCandidatesLoading(state, action) {
      state.relatedData.isServiceCandidatesLoading = action.payload;
    },
    openMaintenanceModeDialog(state, action) {
      state.maintenanceModeDialog.service = action.payload;
    },
    closeMaintenanceModeDialog(state) {
      state.maintenanceModeDialog.service = null;
    },
  },
  extraReducers(builder) {
    builder.addCase(getServiceCandidates.fulfilled, (state, action) => {
      // remove dependencies to earlier added services
      state.relatedData.serviceCandidates = clearSolvedDependencies(action.payload);
    });
    builder.addCase(getServiceCandidates.rejected, (state) => {
      state.relatedData.serviceCandidates = [];
    });
    builder.addCase(toggleMaintenanceMode.pending, (state) => {
      servicesActionsSlice.caseReducers.closeMaintenanceModeDialog(state);
    });
    builder.addCase(deleteService.pending, (state) => {
      servicesActionsSlice.caseReducers.closeDeleteDialog(state);
    });
  },
});

const {
  openCreateDialog,
  closeCreateDialog,
  openDeleteDialog,
  closeDeleteDialog,
  cleanupActions,
  setIsActionInProgress,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
  setIsServiceCandidatesLoading,
} = servicesActionsSlice.actions;

export {
  addServices,
  deleteServiceWithUpdate as deleteService,
  getServiceCandidates,
  toggleMaintenanceMode,
  openCreateDialog,
  closeCreateDialog,
  openDeleteDialog,
  closeDeleteDialog,
  openMaintenanceModeDialog,
  closeMaintenanceModeDialog,
  addServicesWithUpdate,
  cleanupActions,
  setIsActionInProgress,
};

export default servicesActionsSlice.reducer;
