import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { defaultSpinnerDelay } from '@constants';
import { AdcmService, AdcmPrototype, AdcmLicenseStatus } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { updateIfExists } from '@utils/objectUtils';
import { AdcmPrototypesApi, RequestError } from '@api';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

type AdcmServicesState = {
  services: AdcmService[];
  serviceLicense: Omit<AdcmPrototype, 'type' | 'description' | 'bundleId'>[] | [];
  totalCount: number;
  isLoading: boolean;
};

interface LoadClusterServicesPayload {
  clusterId: number;
}

const loadClusterServiceFromBackend = createAsyncThunk(
  'adcm/services/loadClusterServiceFromBackend',
  async ({ clusterId }: LoadClusterServicesPayload, thunkAPI) => {
    const {
      adcm: {
        servicesTable: { filter, sortParams, paginationParams },
      },
    } = thunkAPI.getState();

    try {
      const services = await AdcmClusterServicesApi.getClusterServices(clusterId, filter, sortParams, paginationParams);
      return services;
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServices = createAsyncThunk('adcm/services/getServices', async (arg: LoadClusterServicesPayload, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  await thunkAPI.dispatch(loadClusterServiceFromBackend(arg));
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const getServicesLicenses = createAsyncThunk(
  'adcm/services/getServicesLicenses',
  async (serviceIds: number[], thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    const {
      adcm: {
        servicesActions: {
          relatedData: { servicePrototypes },
        },
      },
    } = thunkAPI.getState();

    thunkAPI.dispatch(cleanupServiceLicense());

    servicePrototypes
      .filter((service) => serviceIds.includes(service.id) && service.licenseStatus === AdcmLicenseStatus.Unaccepted)
      .map((service) => {
        thunkAPI.dispatch(getServiceLicense(service.id));
      });
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,
      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const getServiceLicense = createAsyncThunk('adcm/services/getServiceLicense', async (serviceId: number, thunkAPI) => {
  try {
    const serviceLicense = await AdcmPrototypesApi.getPrototype(serviceId);

    return serviceLicense;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue([]);
  }
});

const acceptServiceLicense = createAsyncThunk(
  'adcm/servicesActions/acceptServiceLicense',
  async (serviceId: number, thunkAPI) => {
    try {
      await AdcmPrototypesApi.postAcceptLicense(serviceId);
      thunkAPI.dispatch(showInfo({ message: 'License was accepted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const refreshServices = createAsyncThunk(
  'adcm/services/refreshServices',
  async (arg: LoadClusterServicesPayload, thunkAPI) => {
    thunkAPI.dispatch(loadClusterServiceFromBackend(arg));
  },
);

const createInitialState = (): AdcmServicesState => ({
  services: [],
  serviceLicense: [],
  totalCount: 0,
  isLoading: false,
});

const servicesSlice = createSlice({
  name: 'adcm/services',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupServices() {
      return createInitialState();
    },
    cleanupServiceLicense(state) {
      state.serviceLicense = [];
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServiceFromBackend.fulfilled, (state, action) => {
      state.services = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadClusterServiceFromBackend.rejected, (state) => {
      state.services = [];
    });
    builder.addCase(getServiceLicense.fulfilled, (state, action) => {
      const prototypeId = action.meta.arg;
      const service = state.serviceLicense.find((service) => service.id === prototypeId);
      if (!service) {
        state.serviceLicense = [...state.serviceLicense, action.payload];
      }
    });
    builder.addCase(getServiceLicense.rejected, (state) => {
      state.serviceLicense = [];
    });
    builder.addCase(acceptServiceLicense.fulfilled, (state, action) => {
      const serviceId = action.meta.arg;
      const service = state.serviceLicense.find((service) => service.id === serviceId);
      if (service) {
        service.license.status = AdcmLicenseStatus.Accepted;
        const licenses = [...state.serviceLicense, service];
        state.serviceLicense = [...new Set(licenses)];
      }
    });
    builder.addCase(wsActions.update_service, (state, action) => {
      const { id, changes } = action.payload.object;
      state.services = updateIfExists<AdcmService>(
        state.services,
        (service) => service.id === id,
        () => changes,
      );
    });
    builder.addCase(wsActions.create_service_concern, (state, action) => {
      const { id: serviceId, changes: newConcern } = action.payload.object;
      state.services = updateIfExists<AdcmService>(
        state.services,
        (service) => service.id === serviceId && service.concerns.every((concern) => concern.id !== newConcern.id),
        (service) => ({
          concerns: [...service.concerns, newConcern],
        }),
      );
    });
    builder.addCase(wsActions.delete_service_concern, (state, action) => {
      const { id: serviceId, changes } = action.payload.object;
      state.services = updateIfExists<AdcmService>(
        state.services,
        (service) => service.id === serviceId,
        (service) => ({
          concerns: service.concerns.filter((concern) => concern.id !== changes.id),
        }),
      );
    });
  },
});

export const { setIsLoading, cleanupServices, cleanupServiceLicense } = servicesSlice.actions;
export { getServices, refreshServices, getServicesLicenses, getServiceLicense, acceptServiceLicense };

export default servicesSlice.reducer;
