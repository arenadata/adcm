import type { RequestError } from '@api';
import { AdcmClusterServiceComponentsApi } from '@api';
import type { AdcmServiceComponent } from '@models/adcm';
import { AdcmMaintenanceMode } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { showError, showInfo } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';

interface AdcmServiceComponentState {
  serviceComponent?: AdcmServiceComponent;
  isLoading: boolean;
}

interface LoadClusterServiceComponentPayload {
  clusterId: number;
  serviceId: number;
  componentId: number;
}

const loadClusterServiceComponentFromBackend = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponent/loadClusterServiceComponentFromBackend',
  async ({ clusterId, serviceId, componentId }: LoadClusterServiceComponentPayload, thunkAPI) => {
    try {
      const component = await AdcmClusterServiceComponentsApi.getServiceComponent(clusterId, serviceId, componentId);
      return component;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: 'Component not found' }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServiceComponent = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponent/getServiceComponent',
  async (arg: LoadClusterServiceComponentPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadClusterServiceComponentFromBackend(arg));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,

      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

interface toggleMaintenanceModePayload extends LoadClusterServiceComponentPayload {
  maintenanceMode: AdcmMaintenanceMode;
}

const toggleMaintenanceMode = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponent/toggleMaintenanceMode',
  async ({ clusterId, serviceId, componentId, maintenanceMode }: toggleMaintenanceModePayload, thunkAPI) => {
    try {
      const data = await AdcmClusterServiceComponentsApi.toggleMaintenanceMode(
        clusterId,
        serviceId,
        componentId,
        maintenanceMode,
      );
      const maintenanceModeStatus = maintenanceMode === AdcmMaintenanceMode.Off ? 'disabled' : 'enabled';
      thunkAPI.dispatch(showInfo({ message: `The maintenance mode has been ${maintenanceModeStatus}` }));
      return data;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): AdcmServiceComponentState => ({
  serviceComponent: undefined,
  isLoading: true,
});

const serviceComponentSlice = createSlice({
  name: 'adcm/cluster/services/serviceComponents/serviceComponent',
  initialState: createInitialState(),
  reducers: {
    cleanupServiceComponent: () => {
      return createInitialState();
    },
    setIsLoading: (state, action) => {
      state.isLoading = action.payload;
    },
  },
  extraReducers(builder) {
    builder.addCase(loadClusterServiceComponentFromBackend.fulfilled, (state, action) => {
      state.serviceComponent = action.payload;
    });
    builder.addCase(loadClusterServiceComponentFromBackend.rejected, (state) => {
      state.serviceComponent = undefined;
    });
    builder.addCase(toggleMaintenanceMode.fulfilled, (state, action) => {
      if (state.serviceComponent) {
        state.serviceComponent.maintenanceMode = action.payload.maintenanceMode;
      }
    });
    builder.addCase(wsActions.update_component, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.serviceComponent?.id === id) {
        state.serviceComponent = {
          ...state.serviceComponent,
          ...changes,
        };
      }
    });
    builder.addCase(wsActions.create_component_concern, (state, action) => {
      const { id: serviceComponentId, changes: newConcern } = action.payload.object;
      if (
        state.serviceComponent?.id === serviceComponentId &&
        state.serviceComponent.concerns.every((concern) => concern.id !== newConcern.id)
      ) {
        state.serviceComponent = {
          ...state.serviceComponent,
          concerns: [...state.serviceComponent.concerns, newConcern],
        };
      }
    });
    builder.addCase(wsActions.delete_component_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      if (state.serviceComponent?.id === id) {
        state.serviceComponent = {
          ...state.serviceComponent,
          concerns: state.serviceComponent.concerns.filter((concern) => concern.id !== changes.id),
        };
      }
    });
  },
});

const { cleanupServiceComponent, setIsLoading } = serviceComponentSlice.actions;
export { cleanupServiceComponent, loadClusterServiceComponentFromBackend, getServiceComponent, toggleMaintenanceMode };
export default serviceComponentSlice.reducer;
