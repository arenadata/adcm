import { AdcmClusterHostsApi, RequestError } from '@api';
import { defaultSpinnerDelay } from '@constants';
import { AdcmServiceComponent } from '@models/adcm';
import { createSlice } from '@reduxjs/toolkit';
import { wsActions } from '@store/middlewares/wsMiddleware.constants';
import { showError } from '@store/notificationsSlice';
import { createAsyncThunk } from '@store/redux';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { updateIfExists } from '@utils/objectUtils';
import { executeWithMinDelay } from '@utils/requestUtils';

interface AdcmHostComponentsState {
  isLoading: boolean;
  hostComponents: AdcmServiceComponent[];
  totalCount: number;
}

interface ClusterHostComponentsPayload {
  clusterId: number;
  hostId: number;
}

const loadHostComponents = createAsyncThunk(
  'adcm/hostComponents/loadHostComponents',
  async ({ clusterId, hostId }: ClusterHostComponentsPayload, thunkAPI) => {
    const {
      adcm: {
        hostComponentsTable: { paginationParams, filter, sortParams },
      },
    } = thunkAPI.getState();
    try {
      const clusterHostComponents = await AdcmClusterHostsApi.getClusterHostComponents(
        clusterId,
        hostId,
        sortParams,
        paginationParams,
        filter,
      );
      return clusterHostComponents;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const getHostComponents = createAsyncThunk(
  'adcm/hostComponents/getHostComponents',
  async (arg: ClusterHostComponentsPayload, thunkAPI) => {
    thunkAPI.dispatch(setIsLoading(true));
    const startDate = new Date();

    await thunkAPI.dispatch(loadHostComponents(arg));

    executeWithMinDelay({
      startDate,
      delay: defaultSpinnerDelay,

      callback: () => {
        thunkAPI.dispatch(setIsLoading(false));
      },
    });
  },
);

const refreshHostComponents = createAsyncThunk(
  'adcm/hostComponents/refreshHostComponents',
  async (arg: ClusterHostComponentsPayload, thunkAPI) => {
    thunkAPI.dispatch(loadHostComponents(arg));
  },
);

const createInitialState = (): AdcmHostComponentsState => ({
  isLoading: true,
  hostComponents: [],
  totalCount: 0,
});

const hostComponentsSlice = createSlice({
  name: 'adcm/hostComponents',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupHostComponents() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadHostComponents.fulfilled, (state, action) => {
      state.hostComponents = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadHostComponents.rejected, (state) => {
      state.hostComponents = [];
    });

    builder.addCase(wsActions.update_component, (state, action) => {
      const { id, changes } = action.payload.object;
      state.hostComponents = updateIfExists<AdcmServiceComponent>(
        state.hostComponents,
        (hostComponent) => hostComponent.id === id,
        () => changes,
      );
    });
    builder.addCase(wsActions.create_component_concern, (state, action) => {
      const { id: hostComponentId, changes: newConcern } = action.payload.object;
      state.hostComponents = updateIfExists<AdcmServiceComponent>(
        state.hostComponents,
        (hostComponent) =>
          hostComponent.id === hostComponentId &&
          hostComponent.concerns.every((concern) => concern.id !== newConcern.id),
        (hostComponent) => ({
          concerns: [...hostComponent.concerns, newConcern],
        }),
      );
    });
    builder.addCase(wsActions.delete_component_concern, (state, action) => {
      const { id, changes } = action.payload.object;
      state.hostComponents = updateIfExists<AdcmServiceComponent>(
        state.hostComponents,
        (hostComponent) => hostComponent.id === id,
        (hostComponent) => ({
          concerns: hostComponent.concerns.filter((concern) => concern.id !== changes.id),
        }),
      );
    });
  },
});

const { setIsLoading, cleanupHostComponents } = hostComponentsSlice.actions;
export { getHostComponents, refreshHostComponents, cleanupHostComponents };
export default hostComponentsSlice.reducer;
