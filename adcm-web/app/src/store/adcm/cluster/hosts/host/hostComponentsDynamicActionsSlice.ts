import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { AdcmClusterHostsApi, RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showInfo } from '@store/notificationsSlice';
import { AdcmDynamicAction, AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm/dynamicAction';
import { getErrorMessage } from '@utils/httpResponseUtils';

interface LoadClusterHostComponentsDynamicActions {
  clusterId: number;
  hostId: number;
  componentsPrototypesIds: number[];
}

const loadClusterHostComponentsDynamicActions = createAsyncThunk(
  'adcm/hosts/hostComponents/hostComponentDynamicActions/loadClusterHostComponentsDynamicActions',
  async ({ clusterId, hostId, componentsPrototypesIds }: LoadClusterHostComponentsDynamicActions, thunkAPI) => {
    try {
      const actionsPromises = await Promise.allSettled(
        componentsPrototypesIds.map(async (componentPrototypeId) => {
          return {
            componentPrototypeId,
            dynamicActions: await AdcmClusterHostsApi.getClusterHostComponentActions(
              clusterId,
              hostId,
              componentPrototypeId,
            ),
          };
        }),
      );
      const hostComponentsActions = fulfilledFilter(actionsPromises);
      if (hostComponentsActions.length === 0 && componentsPrototypesIds.length > 0) {
        throw new Error('All host components cannot get those actions');
      }

      if (hostComponentsActions.length < componentsPrototypesIds.length) {
        throw new Error('Some host components cannot get those actions');
      }

      return hostComponentsActions.reduce((res, { componentPrototypeId, dynamicActions }) => {
        res[componentPrototypeId] = dynamicActions;

        return res;
      }, {} as AdcmClusterHostComponentsDynamicActionsState['hostComponentDynamicActions']);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

interface OpenClusterHostComponentDynamicActionPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
}

const openClusterHostComponentDynamicActionDialog = createAsyncThunk(
  'adcm/hosts/hostComponents/hostComponentDynamicActions/openClusterHostComponentDynamicActionDialog',
  async ({ clusterId, hostId, actionId }: OpenClusterHostComponentDynamicActionPayload, thunkAPI) => {
    try {
      const actionDetails = await AdcmClusterHostsApi.getClusterHostActionsDetails(clusterId, hostId, actionId);

      return actionDetails;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

interface RunClusterHostComponentDynamicActionPayload {
  clusterId: number;
  hostId: number;
  actionId: number;
  actionRunConfig: AdcmDynamicActionRunConfig;
}

const runClusterHostComponentDynamicAction = createAsyncThunk(
  'adcm/hosts/hostComponents/hostComponentDynamicActions/runClusterHostComponentDynamicAction',
  async ({ clusterId, hostId, actionId, actionRunConfig }: RunClusterHostComponentDynamicActionPayload, thunkAPI) => {
    try {
      // TODO: run***Action get big response with information about action, but wiki say that this should empty response
      await AdcmClusterHostsApi.runClusterHostAction(clusterId, hostId, actionId, actionRunConfig);

      thunkAPI.dispatch(showInfo({ message: 'Action was running successfully' }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

type AdcmClusterHostComponentsDynamicActionsState = {
  dialog: {
    actionDetails: AdcmDynamicActionDetails | null;
    clusterId: number | null;
    hostId: number | null;
  };
  hostComponentDynamicActions: Record<number, AdcmDynamicAction[]>;
};

const createInitialState = (): AdcmClusterHostComponentsDynamicActionsState => ({
  dialog: {
    actionDetails: null,
    clusterId: null,
    hostId: null,
  },
  hostComponentDynamicActions: {},
});

const hostComponentsDynamicActionsSlice = createSlice({
  name: 'adcm/hostComponentsDynamicActionsSlice',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterHostComponentsDynamicActions() {
      return createInitialState();
    },
    closeClusterHostComponentsDynamicActionDialog(state) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.dialog = createInitialState().dialog;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterHostComponentsDynamicActions.fulfilled, (state, action) => {
      state.hostComponentDynamicActions = action.payload;
    });
    builder.addCase(loadClusterHostComponentsDynamicActions.rejected, (state) => {
      state.hostComponentDynamicActions = [];
    });
    builder.addCase(openClusterHostComponentDynamicActionDialog.fulfilled, (state, action) => {
      state.dialog.actionDetails = action.payload;
      state.dialog.clusterId = action.meta.arg.clusterId;
      state.dialog.hostId = action.meta.arg.hostId;
    });
    builder.addCase(openClusterHostComponentDynamicActionDialog.rejected, (state) => {
      hostComponentsDynamicActionsSlice.caseReducers.closeClusterHostComponentsDynamicActionDialog(state);
    });
    builder.addCase(runClusterHostComponentDynamicAction.pending, (state) => {
      hostComponentsDynamicActionsSlice.caseReducers.closeClusterHostComponentsDynamicActionDialog(state);
    });
  },
});

export const { cleanupClusterHostComponentsDynamicActions, closeClusterHostComponentsDynamicActionDialog } =
  hostComponentsDynamicActionsSlice.actions;
export {
  loadClusterHostComponentsDynamicActions,
  openClusterHostComponentDynamicActionDialog,
  runClusterHostComponentDynamicAction,
};

export default hostComponentsDynamicActionsSlice.reducer;
