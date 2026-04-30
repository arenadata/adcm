import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import type { RequestError } from '@api';
import { fulfilledFilter } from '@utils/promiseUtils';
import { showError, showSuccess } from '@store/notificationsSlice';
import type { AdcmActionHostGroup, AdcmDynamicActionDetails, EntitiesDynamicActions } from '@models/adcm';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { ActionStatuses } from '@constants';
import { services } from '@store/adcm/entityActionHostGroups/actionHostGroupsSlice.constants';
import type {
  GetActionHostGroupDynamicActionsActionPayload,
  OpenDynamicActionActionPayload,
  RunActionHostGroupDynamicActionActionPayload,
} from '../entityActionHostGroups/actionHostGroups.types';
import type { AdcmCreateProcessPayload } from '../entityWizard/types/wizardSlice.types';
import { createProcess } from '../entityWizard/wizardActionsSlice';

const loadDynamicActions = createAsyncThunk(
  'adcm/dynamicActions/loadDynamicActions',
  async ({ entityType, entityArgs, actionHostGroupIds }: GetActionHostGroupDynamicActionsActionPayload, thunkAPI) => {
    try {
      const service = services[entityType];
      const actionsPromises = await Promise.allSettled(
        actionHostGroupIds.map(async (actionHostGroupId) => ({
          actionHostGroupId,
          dynamicActions: await service.getActionHostGroupActions({ ...entityArgs, actionHostGroupId }),
        })),
      );

      const dynamicActionsResponses = fulfilledFilter(actionsPromises);

      if (dynamicActionsResponses.length === 0 && actionHostGroupIds.length > 0) {
        throw new Error('All action host groups can not get those actions');
      }

      if (dynamicActionsResponses.length < actionHostGroupIds.length) {
        throw new Error('Some action host groups can not get those actions');
      }

      const r = dynamicActionsResponses.reduce((res, { actionHostGroupId, dynamicActions }) => {
        res[actionHostGroupId] = dynamicActions;

        return res;
      }, {} as EntitiesDynamicActions);
      return r;
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      thunkAPI.dispatch(showError({ message: error.message }));
      return thunkAPI.rejectWithValue([]);
    }
  },
);

const openDynamicActionDialog = createAsyncThunk(
  'adcm/dynamicActions/openDynamicActionDialog',
  async ({ entityType, entityArgs, actionHostGroupId, actionId }: OpenDynamicActionActionPayload, thunkAPI) => {
    try {
      const service = services[entityType];
      const actionDetails = await service.getActionHostGroupAction({ ...entityArgs, actionHostGroupId, actionId });
      const actionHostGroup = await service.getActionHostGroup({ ...entityArgs, actionHostGroupId });

      return { actionDetails, actionHostGroup };
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

const runDynamicAction = createAsyncThunk(
  'adcm/dynamicActions/runDynamicAction',
  async (
    {
      entityType,
      entityArgs,
      actionHostGroupId,
      actionId,
      actionRunConfig,
    }: RunActionHostGroupDynamicActionActionPayload,
    thunkAPI,
  ) => {
    try {
      const service = services[entityType];
      await service.postActionHostGroupAction({ ...entityArgs, actionHostGroupId, actionId, actionRunConfig });

      thunkAPI.dispatch(showSuccess({ message: ActionStatuses.SuccessRun }));

      return null;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(null);
    }
  },
);

const createWizardProcess = createAsyncThunk(
  'adcm/dynamicActions/createWizardProcess',
  async ({ entityType, entityArgs, actionId }: AdcmCreateProcessPayload, thunkAPI) => {
    const {
      adcm: {
        dynamicActions: { actionHostGroup },
      },
    } = thunkAPI.getState();

    return await thunkAPI
      .dispatch(createProcess({ entityType, entityArgs, actionHostGroupId: actionHostGroup?.id as number, actionId }))
      .unwrap();
  },
);

type AdcmDynamicActionsState = {
  actionHostGroup: AdcmActionHostGroup | null;
  actionDetails: AdcmDynamicActionDetails | null;
  dynamicActions: EntitiesDynamicActions;
};

const createInitialState = (): AdcmDynamicActionsState => ({
  actionHostGroup: null,
  actionDetails: null,
  dynamicActions: {},
});

const dynamicActionsSlice = createSlice({
  name: 'adcm/dynamicActions',
  initialState: createInitialState(),
  reducers: {
    cleanupDynamicActions() {
      return createInitialState();
    },
    closeDynamicActionDialog(state) {
      state.actionDetails = null;
      state.actionHostGroup = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadDynamicActions.fulfilled, (state, action) => {
      state.dynamicActions = action.payload;
    });
    builder.addCase(loadDynamicActions.rejected, (state) => {
      state.dynamicActions = [];
    });
    builder.addCase(openDynamicActionDialog.fulfilled, (state, action) => {
      const { actionDetails, actionHostGroup } = action.payload;
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-ignore
      state.actionDetails = actionDetails;
      state.actionHostGroup = actionHostGroup;
    });
    builder.addCase(createWizardProcess.fulfilled, (state, action) => {
      const process = action.payload;
      state.actionDetails?.processes?.push(process);
    });
    builder.addCase(openDynamicActionDialog.rejected, (state) => {
      state.actionDetails = null;
      state.actionHostGroup = null;
    });
    builder.addCase(runDynamicAction.pending, (state) => {
      state.actionDetails = null;
      state.actionHostGroup = null;
    });
  },
});

export const { cleanupDynamicActions, closeDynamicActionDialog } = dynamicActionsSlice.actions;
export { loadDynamicActions, openDynamicActionDialog, runDynamicAction, createWizardProcess };

export default dynamicActionsSlice.reducer;
