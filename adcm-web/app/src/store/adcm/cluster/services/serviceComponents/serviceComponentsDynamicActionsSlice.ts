import { createSlice } from '@reduxjs/toolkit';
import { AdcmCluster, AdcmService, AdcmServiceComponent } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterServiceComponentsApi, RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { ActionStatuses } from '@constants';

interface LoadClusterServiceComponentsDynamicActions {
  components: AdcmServiceComponent[];
}

const loadClusterServiceComponentsDynamicActions = createAsyncThunk(
  'adcm/services/serviceComponents/serviceComponentDynamicActions/loadClusterServiceComponentsDynamicActions',
  async ({ components }: LoadClusterServiceComponentsDynamicActions, thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        components.map(async (component) => {
          const {
            id: componentId,
            cluster: { id: clusterId },
            service: { id: serviceId },
          } = component;
          return {
            componentId,
            dynamicActions: await AdcmClusterServiceComponentsApi.getClusterServiceComponentsActions(
              clusterId,
              serviceId,
              componentId,
            ),
          };
        }),
      );
      const serviceComponentsActions = fulfilledFilter(actionsPromises);
      if (serviceComponentsActions.length === 0 && components.length > 0) {
        throw new Error('All service components cannot get those actions');
      }

      if (serviceComponentsActions.length < components.length) {
        throw new Error('Some service components cannot get those actions');
      }

      return serviceComponentsActions.reduce((res, { componentId, dynamicActions }) => {
        res[componentId] = dynamicActions;

        return res;
      }, {} as AdcmClusterServiceComponentsDynamicActionsState['serviceComponentDynamicActions']);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenClusterServiceComponentDynamicActionPayload {
  component: AdcmServiceComponent;
  actionId: number;
}

const openClusterServiceComponentDynamicActionDialog = createAsyncThunk(
  'adcm/services/serviceComponents/serviceComponentDynamicActions/openClusterServiceComponentDynamicActionDialog',
  async ({ component, actionId }: OpenClusterServiceComponentDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmClusterServiceComponentsApi.getClusterServiceComponentActionDetails(
        component.cluster.id,
        component.service.id,
        component.id,
        actionId,
      );

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunClusterServiceComponentDynamicActionPayload {
  component: AdcmServiceComponent;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterServiceComponentDynamicAction = createAsyncThunk(
  'adcm/services/serviceComponents/serviceComponentDynamicActions/runClusterServiceComponentDynamicAction',
  async ({ component, actionId, actionRunConfig }: RunClusterServiceComponentDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmClusterServiceComponentsApi.runClusterServiceComponentAction(
        component.cluster.id,
        component.service.id,
        component.id,
        actionId,
        actionRunConfig,
      );

      thunkAPI.dispatch(showInfo({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmClusterServiceComponentsDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    cluster: AdcmCluster | null;
    service: AdcmService | null;
    component: AdcmServiceComponent | null;
  };
  serviceComponentDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmClusterServiceComponentsDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    cluster: null,
    service: null,
    component: null,
  },
  serviceComponentDynamicActions: {},
});

const serviceComponentsDynamicActionsSlice = createSlice({
  name: 'adcm/serviceComponentsDynamicActionsSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServiceComponentsDynamicActions() {
      return createInitialState();
    },
    closeClusterServiceComponentsDynamicActionDialog(state) {
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServiceComponentsDynamicActions.fulfilled, (state, action) => {
      state.serviceComponentDynamicActions = action.payload;
    });
    builder.addCase(loadClusterServiceComponentsDynamicActions.rejected, (state) => {
      state.serviceComponentDynamicActions = [];
    });
    builder.addCase(openClusterServiceComponentDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.component = action.meta.arg.component;
    });
    builder.addCase(openClusterServiceComponentDynamicActionDialog.rejected, (state) => {
      serviceComponentsDynamicActionsSlice.caseReducers.closeClusterServiceComponentsDynamicActionDialog(state);
    });
    builder.addCase(runClusterServiceComponentDynamicAction.pending, (state) => {
      serviceComponentsDynamicActionsSlice.caseReducers.closeClusterServiceComponentsDynamicActionDialog(state);
    });
  },
});

export const { cleanupClusterServiceComponentsDynamicActions, closeClusterServiceComponentsDynamicActionDialog } =
  serviceComponentsDynamicActionsSlice.actions;
export {
  loadClusterServiceComponentsDynamicActions,
  openClusterServiceComponentDynamicActionDialog,
  runClusterServiceComponentDynamicAction,
};

export default serviceComponentsDynamicActionsSlice.reducer;
