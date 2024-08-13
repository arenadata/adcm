import { PayloadAction, createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { getActionHostGroups } from '@store/adcm/entityActionHostGroups/actionHostGroupsSlice';
import { showError, showInfo, showSuccess } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { RequestError } from '@api';
import { ActionState } from '@models/loadState';
import { services } from './actionHostGroupsSlice.constants';
import type {
  OpenCreateDialogActionPayload,
  LoadCreateDialogRelatedDataActionPayload,
  CreateActionHostGroupActionPayload,
  OpenEditDialogActionPayload,
  LoadEditDialogRelatedDataActionPayload,
  UpdateActionHostGroupActionPayload,
  OpenDeleteDialogActionPayload,
  DeleteActionHostGroupActionPayload,
} from './actionHostGroups.types';
import type { AdcmActionHostGroup, AdcmActionHostGroupHost } from '@models/adcm';
import { splitHosts } from './actionHostGroupsActionsSlice.utils';
import { fulfilledFilter } from '@utils/promiseUtils';

const openCreateDialog = createAsyncThunk(
  'adcm/actionHostsGroupsActions/openCreateDialog',
  async (args: OpenCreateDialogActionPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(loadCreateRelatedData(args));
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadCreateRelatedData = createAsyncThunk(
  'adcm/actionHostsGroupsActions/loadCreateRelatedData',
  async ({ entityType, entityArgs }: LoadCreateDialogRelatedDataActionPayload) => {
    const service = services[entityType];
    const hostCandidates = await service.getActionHostGroupsHostCandidates({ ...entityArgs, filter: {} });
    return { hostCandidates };
  },
);

const createActionHostGroup = createAsyncThunk(
  'adcm/actionHostsGroupsActions/createActionHostGroup',
  async ({ entityType, entityArgs, actionHostGroup, hostIds }: CreateActionHostGroupActionPayload, thunkAPI) => {
    try {
      const service = services[entityType];
      thunkAPI.dispatch(setCreatingState('in-progress'));
      const host = await service.postActionHostGroup({ ...entityArgs, actionHostGroup });

      const promises = [];
      for (const id of hostIds.values()) {
        promises.push(
          service.postActionHostGroupHost({
            ...entityArgs,
            actionHostGroupId: host.id,
            hostId: id,
          }),
        );
      }

      const totalRequestsCount = hostIds.size;
      const allPromises = await Promise.allSettled(promises);

      const fullfilledPromises = fulfilledFilter(allPromises);
      if (fullfilledPromises.length === 0 && totalRequestsCount > 0) {
        // throw exception because full crash
        throw new Error('All hosts can not mapped on this group');
      }

      if (fullfilledPromises.length < totalRequestsCount) {
        thunkAPI.dispatch(showInfo({ message: 'Some hosts were successfully mapped on this group' }));
        thunkAPI.dispatch(showError({ message: 'Some hosts can not mapped on this group' }));

        // return false because process done with partly success
        return false;
      }

      thunkAPI.dispatch(showSuccess({ message: 'All hosts were successfully mapped on this group' }));
      return true;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setCreatingState('completed'));
    }
  },
);

const createActionHostGroupWithUpdate = createAsyncThunk(
  'adcm/actionHostsGroupsActions/createHostWithUpdate',
  async (args: CreateActionHostGroupActionPayload, thunkAPI) => {
    const { entityType, entityArgs } = args;
    await thunkAPI.dispatch(createActionHostGroup(args)).unwrap();
    await thunkAPI.dispatch(getActionHostGroups({ entityType, entityArgs }));
  },
);

const openEditDialog = createAsyncThunk(
  'adcm/actionHostsGroupsActions/openEditDialog',
  async (args: OpenEditDialogActionPayload, thunkAPI) => {
    try {
      thunkAPI.dispatch(loadEditRelatedData(args));
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const loadEditRelatedData = createAsyncThunk(
  'adcm/actionHostsGroupsActions/loadEditRelatedData',
  async ({ entityType, entityArgs, actionHostGroup }: LoadEditDialogRelatedDataActionPayload) => {
    const service = services[entityType];
    const hostCandidates = await service.getActionHostGroupHostCandidates({
      ...entityArgs,
      filter: {},
      actionHostGroupId: actionHostGroup.id,
    });
    return { hostCandidates };
  },
);

const updateActionHostGroup = createAsyncThunk(
  'adcm/actionHostsGroupsActions/updateActionHostGroup',
  async ({ entityType, entityArgs, actionHostGroup, hostIds }: UpdateActionHostGroupActionPayload, thunkAPI) => {
    try {
      const service = services[entityType];
      thunkAPI.dispatch(setEditingState('in-progress'));

      const addPromises = [];
      const deletePromises = [];

      const { toAdd, toDelete } = splitHosts(actionHostGroup.hosts, hostIds);

      for (const id of toAdd.values()) {
        addPromises.push(
          service.postActionHostGroupHost({
            ...entityArgs,
            actionHostGroupId: actionHostGroup?.id,
            hostId: id,
          }),
        );
      }

      for (const id of toDelete.values()) {
        deletePromises.push(
          service.deleteActionHostGroupHost({
            ...entityArgs,
            actionHostGroupId: actionHostGroup?.id,
            hostId: id,
          }),
        );
      }

      const allPromises = await Promise.allSettled([...addPromises, ...deletePromises]);

      const totalRequestsCount = toAdd.size + toDelete.size;

      const fullfilledPromises = fulfilledFilter(allPromises);
      if (fullfilledPromises.length === 0 && totalRequestsCount > 0) {
        // throw exception because full crash
        throw new Error('All hosts can not mapped on this group');
      }

      if (fullfilledPromises.length < totalRequestsCount) {
        thunkAPI.dispatch(showInfo({ message: 'Some hosts were successfully mapped on this group' }));
        thunkAPI.dispatch(showError({ message: 'Some hosts can not mapped on this group' }));

        // return false because process done with partly success
        return false;
      }

      thunkAPI.dispatch(showSuccess({ message: 'All hosts were successfully mapped on this group' }));
      return true;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(setEditingState('completed'));
    }
  },
);

const updateActionHostGroupWithUpdate = createAsyncThunk(
  'adcm/actionHostsGroupsActions/createHostWithUpdate',
  async (args: UpdateActionHostGroupActionPayload, thunkAPI) => {
    const { entityType, entityArgs } = args;
    await thunkAPI.dispatch(updateActionHostGroup(args)).unwrap();
    await thunkAPI.dispatch(getActionHostGroups({ entityType, entityArgs }));
  },
);

const deleteActionHostGroup = createAsyncThunk(
  'adcm/actionHostsGroupsActions/deleteActionHostGroup',
  async ({ entityType, entityArgs, actionHostGroup }: DeleteActionHostGroupActionPayload, thunkAPI) => {
    try {
      const service = services[entityType];
      await service.deleteActionHostGroup({ ...entityArgs, actionHostGroupId: actionHostGroup.id });
      thunkAPI.dispatch(showSuccess({ message: 'The action host group has been deleted' }));
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const deleteActionHostGroupWithUpdate = createAsyncThunk(
  'adcm/actionHostsGroupsActions/deleteActionHostGroupWithUpdate',
  async (args: DeleteActionHostGroupActionPayload, thunkAPI) => {
    const { entityType, entityArgs } = args;
    await thunkAPI.dispatch(deleteActionHostGroup(args)).unwrap();
    await thunkAPI.dispatch(getActionHostGroups({ entityType, entityArgs }));
  },
);

interface AdcmActionHostGroupsActionsState {
  createDialog: {
    isOpen: boolean;
    creatingState: ActionState;
    relatedData: {
      hostCandidates: AdcmActionHostGroupHost[];
    };
  };
  editDialog: {
    actionHostGroup: AdcmActionHostGroup | null;
    editingState: ActionState;
    relatedData: {
      hostCandidates: AdcmActionHostGroupHost[];
    };
  };
  deleteDialog: {
    actionHostGroup: AdcmActionHostGroup | null;
    deletingState: ActionState;
  };
}

const createInitialState = (): AdcmActionHostGroupsActionsState => ({
  createDialog: {
    isOpen: false,
    creatingState: 'not-started',
    relatedData: {
      hostCandidates: [],
    },
  },
  editDialog: {
    actionHostGroup: null,
    editingState: 'not-started',
    relatedData: {
      hostCandidates: [],
    },
  },
  deleteDialog: {
    actionHostGroup: null,
    deletingState: 'not-started',
  },
});

const actionHostGroupsActionsSlice = createSlice({
  name: 'adcm/actionHostsGroupsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupActions() {
      return createInitialState();
    },
    closeCreateDialog() {
      return createInitialState();
    },
    setCreatingState(state, action: PayloadAction<ActionState>) {
      state.createDialog.creatingState = action.payload;
    },
    setEditingState(state, action: PayloadAction<ActionState>) {
      state.editDialog.editingState = action.payload;
    },
    closeEditDialog() {
      return createInitialState();
    },
    openDeleteDialog(state, action: PayloadAction<OpenDeleteDialogActionPayload>) {
      state.deleteDialog.actionHostGroup = action.payload.actionHostGroup;
    },
    closeDeleteDialog() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(openCreateDialog.fulfilled, (state) => {
      state.createDialog.isOpen = true;
    });
    builder.addCase(loadCreateRelatedData.fulfilled, (state, action) => {
      state.createDialog.relatedData = action.payload;
    });
    builder.addCase(createActionHostGroup.fulfilled, () => {
      return createInitialState();
    });
    builder.addCase(getActionHostGroups.pending, () => {
      return createInitialState();
    });
    builder.addCase(openEditDialog.fulfilled, (state, action) => {
      state.editDialog.actionHostGroup = action.meta.arg.actionHostGroup;
    });
    builder.addCase(loadEditRelatedData.fulfilled, (state, action) => {
      state.editDialog.relatedData = action.payload;
    });
    builder.addCase(updateActionHostGroup.fulfilled, () => {
      return createInitialState();
    });
  },
});

export const {
  closeCreateDialog,
  setCreatingState,
  setEditingState,
  closeEditDialog,
  openDeleteDialog,
  closeDeleteDialog,
  cleanupActions,
} = actionHostGroupsActionsSlice.actions;

export {
  openCreateDialog,
  createActionHostGroupWithUpdate,
  openEditDialog,
  updateActionHostGroupWithUpdate,
  deleteActionHostGroupWithUpdate,
};

export default actionHostGroupsActionsSlice.reducer;
