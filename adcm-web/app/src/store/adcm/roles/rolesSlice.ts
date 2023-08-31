import { createSlice } from '@reduxjs/toolkit';
import { createAsyncThunk } from '@store/redux';
import { executeWithMinDelay } from '@utils/requestUtils';
import { defaultSpinnerDelay } from '@constants';
import { AdcmRole, AdcmRoleProduct } from '@models/adcm';
import { AdcmRolesApi } from '@api';

interface AdcmRolesState {
  roles: AdcmRole[];
  totalCount: number;
  isLoading: boolean;
  products: AdcmRoleProduct[];
}

const loadFromBackend = createAsyncThunk('adcm/roles/loadFromBackend', async (arg, thunkAPI) => {
  const {
    adcm: {
      rolesTable: { filter, paginationParams, sortParams },
    },
  } = thunkAPI.getState();

  try {
    const batch = await AdcmRolesApi.getRoles(filter, sortParams, paginationParams);
    return batch;
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const getRoles = createAsyncThunk('adcm/roles/getRoles', async (arg, thunkAPI) => {
  thunkAPI.dispatch(setIsLoading(true));
  const startDate = new Date();

  thunkAPI.dispatch(loadFromBackend());
  executeWithMinDelay({
    startDate,
    delay: defaultSpinnerDelay,
    callback: () => {
      thunkAPI.dispatch(setIsLoading(false));
    },
  });
});

const getProducts = createAsyncThunk('adcm/roles/getProducts', async (arg, thunkAPI) => {
  try {
    return await AdcmRolesApi.getProducts();
  } catch (error) {
    return thunkAPI.rejectWithValue(error);
  }
});

const refreshRoles = createAsyncThunk('adcm/roles/refreshRoles', async (arg, thunkAPI) => {
  thunkAPI.dispatch(loadFromBackend());
});

const createInitialState = (): AdcmRolesState => ({
  roles: [],
  totalCount: 0,
  isLoading: false,
  products: [],
});

const rolesSlice = createSlice({
  name: 'adcm/roles',
  initialState: createInitialState(),
  reducers: {
    setIsLoading(state, action) {
      state.isLoading = action.payload;
    },
    cleanupRoles() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loadFromBackend.fulfilled, (state, action) => {
        state.roles = action.payload.results;
        state.totalCount = action.payload.count;
      })
      .addCase(loadFromBackend.rejected, (state) => {
        state.roles = [];
      })
      .addCase(getProducts.fulfilled, (state, action) => {
        state.products = action.payload.results;
      });
  },
});

const { setIsLoading, cleanupRoles } = rolesSlice.actions;
export { getRoles, getProducts, refreshRoles, cleanupRoles };
export default rolesSlice.reducer;
