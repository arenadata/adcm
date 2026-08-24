import { createSlice } from '@reduxjs/toolkit';
import { AdcmClusterOverviewApi } from '@api';
import { EMPTY_ARRAY } from '@constants';
import { AdcmMaintenanceMode } from '@models/adcm';
import { createAsyncThunk } from '@store/redux';
import { LoadState } from '@models/loadState';

export type MaintenanceEntityItem = {
  id: number;
  name: string;
};

type ClusterMaintenanceModeData = {
  services: MaintenanceEntityItem[];
  hosts: MaintenanceEntityItem[];
  servicesCount: number;
  hostsCount: number;
};

type ClusterMaintenanceModeState = {
  byClusterId: Record<number, ClusterMaintenanceModeData>;
  loadState: LoadState;
};

const emptyPagination = { pageNumber: 0, perPage: 50 };

const loadClusterMaintenanceMode = createAsyncThunk(
  'adcm/clusters/maintenanceMode/load',
  async (clusterId: number, thunkAPI) => {
    try {
      const [servicesResponse, hostsResponse] = await Promise.all([
        AdcmClusterOverviewApi.getClusterServicesStatuses(
          clusterId,
          emptyPagination,
          undefined,
          AdcmMaintenanceMode.On,
        ),
        AdcmClusterOverviewApi.getClusterHostsStatuses(clusterId, emptyPagination, undefined, AdcmMaintenanceMode.On),
      ]);

      return {
        clusterId,
        servicesCount: servicesResponse.count,
        hostsCount: hostsResponse.count,
        services: servicesResponse.results.map((service) => ({
          id: service.id,
          name: service.displayName || service.name,
        })),
        hosts: hostsResponse.results.map((host) => ({
          id: host.id,
          name: host.displayName || host.name,
        })),
      };
    } catch (error) {
      return thunkAPI.rejectWithValue(error);
    }
  },
);

const createInitialState = (): ClusterMaintenanceModeState => ({
  byClusterId: {},
  loadState: LoadState.NotLoaded,
});

const clusterMaintenanceModeSlice = createSlice({
  name: 'adcm/clusters/maintenanceMode',
  initialState: createInitialState(),
  reducers: {
    cleanupClusterMaintenanceMode() {
      return createInitialState();
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loadClusterMaintenanceMode.pending, (state) => {
      state.loadState = LoadState.Loading;
    });
    builder.addCase(loadClusterMaintenanceMode.fulfilled, (state, action) => {
      const { clusterId, services, hosts, servicesCount, hostsCount } = action.payload;
      state.byClusterId[clusterId] = { services, hosts, servicesCount, hostsCount };
      state.loadState = LoadState.Loaded;
    });
    builder.addCase(loadClusterMaintenanceMode.rejected, (state, action) => {
      const clusterId = action.meta.arg;

      if (clusterId) {
        state.byClusterId[clusterId] = {
          services: EMPTY_ARRAY,
          hosts: EMPTY_ARRAY,
          servicesCount: 0,
          hostsCount: 0,
        };
      }

      state.loadState = LoadState.Loaded;
    });
  },
});

const { cleanupClusterMaintenanceMode } = clusterMaintenanceModeSlice.actions;
export { loadClusterMaintenanceMode, cleanupClusterMaintenanceMode };
export default clusterMaintenanceModeSlice.reducer;
