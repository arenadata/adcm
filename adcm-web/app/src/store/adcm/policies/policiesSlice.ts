import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { showError } from '@store/notificationsSlice';
import { getErrorMessage } from '@utils/httpResponseUtils';
import { AdcmPolicy } from '@models/adcm/policy';
import { AdcmPoliciesApi, RequestError } from '@api';

interface AdcmPoliciesState {
  policies: AdcmPolicy[];
  totalCount: number;
  isLoading: boolean;
}

const loadPoliciesFromBackend = createAsyncThunk('adcm/policies/loadPoliciesFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      policiesTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmPoliciesApi.getPolicies(filter, paginationParams, sortParams);
    return batch;
  } catch (error) {
    thunkAPI.dispatch(showError({ message: getErrorMessage(error as RequestError) }));
    return thunkAPI.rejectWithValue(error);
  }
});

const getPolicies = createAsyncThunk('adcm/policies/getPolicies', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadPoliciesFromBackend());
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const refreshPolicies = createAsyncThunk('adcm/policies/refreshGroups', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadPoliciesFromBackend());
});

const createInitialState = (): AdcmPoliciesState => ({
  policies: [],
  totalCount: 0,
  isLoading: false,
});

const policiesSlice = createSlice({
  name: 'adcm/policies',
  initialState: createInitialState(),
  reducers: {
    setIsLoading: (state, action) => {
      state.isLoading = action.payload;
    },
    cleanupPolicies: () => {
      return createInitialState();
    },
  },
  extraReducers(builder) {
    builder.addCase(loadPoliciesFromBackend.fulfilled, (state, action) => {
      state.policies = action.payload.results;
      state.totalCount = action.payload.count;
    });
    builder.addCase(loadPoliciesFromBackend.rejected, (state) => {
      state.policies = [];
    });
  },
});

const { setIsLoading, cleanupPolicies } = policiesSlice.actions;
export { getPolicies, refreshPolicies, cleanupPolicies };
export default policiesSlice.reducer;
