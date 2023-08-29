import { AdcmClusterServiceComponentsApi, RequestError } from '@api';
import { AdcmServiceComponent } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';

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
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getServiceComponent = createAsyncThunk(
  'adcm/cluster/services/serviceComponents/serviceComponent/getServiceComponent',
  async (arg: LoadClusterServiceComponentPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    thunkAPI.dispatch(loadClusterServiceComponentFromBackend(arg));
    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,

      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const createInitialState = (): AdcmServiceComponentState => ({
  serviceComponent: undefined,
  isLoading: false,
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
  },
});

const { cleanupServiceComponent, setIsLoading } = serviceComponentSlice.actions;
export { cleanupServiceComponent, loadClusterServiceComponentFromBackend, getServiceComponent };
export default serviceComponentSlice.reducer;
