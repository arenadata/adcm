import { Middleware } from 'redux';
import { CreateConcernEvent } from '@models/adcm';
import { AppDispatch, StoreState } from '../store';
import { refreshClusters } from '@store/adcm/clusters/clustersSlice';
import { getCluster } from '@store/adcm/clusters/clusterSlice';
import { refreshServices } from '@store/adcm/cluster/services/servicesSlice';
import { getService } from '@store/adcm/services/serviceSlice';
import { refreshServiceComponents } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsSlice';
import { getServiceComponent } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/serviceComponentSlice';
import { getClusterHost, getRelatedClusterHostComponents } from '@store/adcm/cluster/hosts/host/clusterHostSlice';
import { refreshHostProviders } from '@store/adcm/hostProviders/hostProvidersSlice';
import { getHostProvider } from '@store/adcm/hostProviders/hostProviderSlice';
import { refreshClusterHosts } from '@store/adcm/cluster/hosts/hostsSlice';
import { refreshHosts } from '@store/adcm/hosts/hostsSlice';
import { getMappings } from '@store/adcm/cluster/mapping/mappingSlice';
import { wsActions } from './wsMiddleware.constants';

export const refreshDataOnNewConcernMiddleware: Middleware<object, StoreState> = (storeApi) => (next) => (action) => {
  const store = storeApi.getState();
  const dispatch = storeApi.dispatch as AppDispatch;
  const payload = action.payload as CreateConcernEvent;

  switch (action.type) {
    case wsActions.create_cluster_concern.type: {
      // Update clusters table
      const clusters = store.adcm.clusters.clusters;
      if (clusters.length) {
        dispatch(refreshClusters());
      }

      // Update cluster page
      const cluster = store.adcm.cluster.cluster;
      if (cluster && cluster.id === payload.object.id) {
        dispatch(getCluster(cluster.id));
      }

      break;
    }
    case wsActions.create_service_concern.type: {
      // Update services table
      const cluster = store.adcm.cluster.cluster;
      const services = store.adcm.services.services;
      if (cluster && services.length) {
        dispatch(refreshServices({ clusterId: cluster.id }));
      }

      // Update service
      const service = store.adcm.service.service;
      if (cluster && service && service.id === payload.object.id) {
        dispatch(getService({ clusterId: cluster.id, serviceId: service.id }));
      }

      break;
    }
    case wsActions.create_component_concern.type: {
      // Update components table
      const cluster = store.adcm.cluster.cluster;
      const service = store.adcm.service.service;
      const components = store.adcm.serviceComponents.serviceComponents;
      if (cluster && service && components.length) {
        dispatch(refreshServiceComponents({ clusterId: cluster.id, serviceId: service.id }));
      }

      // Update component table
      const component = store.adcm.serviceComponent.serviceComponent;
      if (cluster && service && component && component.id === payload.object.id) {
        dispatch(getServiceComponent({ clusterId: cluster.id, serviceId: service.id, componentId: component.id }));
      }

      // Update host components table
      const clusterHost = store.adcm.clusterHost.clusterHost;
      const hostComponents = store.adcm.clusterHost.relatedData.hostComponents;
      if (cluster && clusterHost && hostComponents.length) {
        dispatch(getRelatedClusterHostComponents({ clusterId: cluster.id, hostId: clusterHost.id }));
      }

      break;
    }
    case wsActions.create_hostprovider_concern.type: {
      // Update host providers
      const hostProviders = store.adcm.hostProviders.hostProviders;
      if (hostProviders.length) {
        dispatch(refreshHostProviders());
      }

      // Update host provider
      const hostProvider = store.adcm.hostProvider.hostProvider;
      if (hostProvider && hostProvider.id == payload.object.id) {
        dispatch(getHostProvider(hostProvider.id));
      }

      break;
    }
    case wsActions.create_host_concern.type: {
      // Update hosts
      const cluster = store.adcm.cluster.cluster;
      const clusterHosts = store.adcm.clusterHosts.hosts;
      if (cluster && clusterHosts.length) {
        dispatch(refreshClusterHosts(cluster.id));
      }

      // Update cluster host
      const clusterHost = store.adcm.clusterHost.clusterHost;
      if (cluster && clusterHost && clusterHost.id === payload.object.id) {
        dispatch(getClusterHost({ clusterId: cluster.id, hostId: clusterHost.id }));
      }

      // Update hosts
      const hosts = store.adcm.hosts.hosts;
      if (hosts.length) {
        dispatch(refreshHosts());
      }

      break;
    }
    case wsActions.update_hostcomponentmap.type: {
      // Update mappings
      const cluster = store.adcm.cluster.cluster;
      const clusterMapping = store.adcm.clusterMapping.mapping;

      if (cluster && cluster.id === payload.object.id && clusterMapping.length) {
        dispatch(getMappings({ clusterId: cluster.id }));
      }
    }
  }

  return next(action);
};
