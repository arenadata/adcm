import { createSlice } from '@reduxjs/toolkit';
import { AdcmCluster, AdcmService } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmClusterServicesApi } from '@api/adcm/clusterServices';
import { ActionStatuses } from '@constants';

type LoadServiceDynamicActionsPayload = {
  clusterId: number;
  servicesIds: number[];
};

const loadClusterServicesDynamicActions = createAsyncThunk(
  'adcm/serviceDynamicActions/loadClusterServicesDynamicActions',
  async ({ clusterId, servicesIds }: LoadServiceDynamicActionsPayload, thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        servicesIds.map(async (serviceId) => ({
          serviceId,
          dynamicActions: await AdcmClusterServicesApi.getClusterServiceActions(clusterId, serviceId),
        })),
      );
      const servicesActions = fulfilledFilter(actionsPromises);
      if (servicesActions.length === 0 && servicesIds.length > 0) {
        throw new Error('All services can not get those actions');
      }

      if (servicesActions.length < servicesIds.length) {
        throw new Error('Some services can not get those actions');
      }

      return servicesActions.reduce((res, { serviceId, dynamicActions }) => {
        res[serviceId] = dynamicActions;

        return res;
      }, {} as AdcmClusterServicesDynamicActionsState['serviceDynamicActions']);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenClusterServiceDynamicActionPayload {
  cluster: AdcmCluster;
  service: AdcmService;
  actionId: number;
}

const openClusterServiceDynamicActionDialog = createAsyncThunk(
  'adcm/serviceDynamicActions/openClusterServiceDynamicActionDialog',
  async ({ cluster, service, actionId }: OpenClusterServiceDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmClusterServicesApi.getClusterServiceActionDetails(
        cluster.id,
        service.id,
        actionId,
      );

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunClusterDynamicActionPayload {
  cluster: AdcmCluster;
  service: AdcmService;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterServiceDynamicAction = createAsyncThunk(
  'adcm/serviceDynamicActions/runClusterServiceDynamicAction',
  async ({ cluster, service, actionId, actionRunConfig }: RunClusterDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmClusterServicesApi.runClusterServiceAction(cluster.id, service.id, actionId, actionRunConfig);

      thunkAPI.dispatch(showInfo({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmClusterServicesDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    cluster: AdcmCluster | null;
    service: AdcmService | null;
  };
  serviceDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmClusterServicesDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    cluster: null,
    service: null,
  },
  serviceDynamicActions: {},
});

const servicesDynamicActionsSlice = createSlice({
  name: 'adcm/servicesDynamicActionsSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterServiceDynamicActions() {
      return createInitialState();
    },
    closeClusterServiceDynamicActionDialog(state) {
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterServicesDynamicActions.fulfilled, (state, action) => {
      state.serviceDynamicActions = action.payload;
    });
    builder.addCase(loadClusterServicesDynamicActions.rejected, (state) => {
      state.serviceDynamicActions = [];
    });
    builder.addCase(openClusterServiceDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.cluster = action.meta.arg.cluster;
      state.dialog.service = action.meta.arg.service;
    });
    builder.addCase(openClusterServiceDynamicActionDialog.rejected, (state) => {
      servicesDynamicActionsSlice.caseReducers.closeClusterServiceDynamicActionDialog(state);
    });
    builder.addCase(runClusterServiceDynamicAction.pending, (state) => {
      servicesDynamicActionsSlice.caseReducers.closeClusterServiceDynamicActionDialog(state);
    });
  },
});

export const { cleanupClusterServiceDynamicActions, closeClusterServiceDynamicActionDialog } =
  servicesDynamicActionsSlice.actions;
export { loadClusterServicesDynamicActions, openClusterServiceDynamicActionDialog, runClusterServiceDynamicAction };

export default servicesDynamicActionsSlice.reducer;
