import { AdcmGroupsApi, RequestError } from '@api';
import { createAsyncThunk, createSlice } from '@reduxjs/toolkit';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { getGroups } from './groupsSlice';
import { CreateAdcmGroupPayload } from '@models/adcm';

const createGroup = createAsyncThunk(
  'adcm/groupActions/createGroup',
  async (payload: CreateAdcmGroupPayload, thunkAPI) => {
    try {
      const group = await AdcmGroupsApi.createGroup(payload);
      return group;
    } catch (error) {
      thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
      return thunkAPI.rejectWithValue(error);
    } finally {
      thunkAPI.dispatch(getGroups());
    }
  },
);

interface AdcmGroupsActionsState {
  createDialog: {
    isOpen: boolean;
  };
}

const createInitialState = (): AdcmGroupsActionsState => ({
  createDialog: {
    isOpen: false,
  },
});

const groupsActionsSlice = createSlice({
  name: 'adcm/groupsActions',
  initialState: createInitialState(),
  reducers: {
    cleanupGroups() {
      return createInitialState();
    },
    openCreateDialog(state) {
      state.createDialog.isOpen = true;
    },
    closeCreateDialog(state) {
      state.createDialog.isOpen = false;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(createGroup.fulfilled, (state) => {
      groupsActionsSlice.caseReducers.closeCreateDialog(state);
    });
  },
});

export const { openCreateDialog, closeCreateDialog } = groupsActionsSlice.actions;
export { createGroup };

export default groupsActionsSlice.reducer;
