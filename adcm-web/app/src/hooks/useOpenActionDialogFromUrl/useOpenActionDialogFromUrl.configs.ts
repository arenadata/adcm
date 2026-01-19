import type { EntityConfig } from './useOpenActionDialogFromUrl.types';
import type { AdcmDynamicAction } from '@models/adcm';
import { openClusterDynamicActionDialog } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { openClusterServiceDynamicActionDialog } from '@store/adcm/cluster/services/servicesDynamicActionsSlice';
import { openClusterServiceComponentDynamicActionDialog } from '@store/adcm/cluster/services/serviceComponents/serviceComponentsDynamicActionsSlice';
import { openHostProviderDynamicActionDialog } from '@store/adcm/hostProviders/hostProvidersDynamicActionsSlice';

const EMPTY_DYNAMIC_ACTIONS: AdcmDynamicAction[] = [];

export const clusterActionDialogConfig: EntityConfig<'cluster'> = {
  getEntity: (s) => s.adcm.cluster.cluster,
  getDynamicActions: (s, clusterId) =>
    s.adcm.clustersDynamicActions.clusterDynamicActions[clusterId] ?? EMPTY_DYNAMIC_ACTIONS,
  openDialog: openClusterDynamicActionDialog,
  getEntityParams: (cluster) => ({ cluster }),
};

export const serviceActionDialogConfig: EntityConfig<'service'> = {
  getEntity: (s) => s.adcm.service.service,
  getDynamicActions: (s, serviceId) =>
    s.adcm.servicesDynamicActions.serviceDynamicActions[serviceId] ?? EMPTY_DYNAMIC_ACTIONS,
  openDialog: openClusterServiceDynamicActionDialog,
  getAdditionalData: (s) => ({ cluster: s.adcm.cluster.cluster }),
  getEntityParams: (service, additionalData) => {
    const cluster = additionalData?.cluster;
    if (!cluster) {
      return undefined;
    }
    return { cluster, service };
  },
};

export const componentActionDialogConfig: EntityConfig<'component'> = {
  getEntity: (s) => s.adcm.serviceComponent.serviceComponent,
  getDynamicActions: (s, componentId) =>
    s.adcm.serviceComponentsDynamicActions.serviceComponentDynamicActions[componentId] ?? EMPTY_DYNAMIC_ACTIONS,
  openDialog: openClusterServiceComponentDynamicActionDialog,
  getEntityParams: (component) => ({ component }),
};

export const hostProviderActionDialogConfig: EntityConfig<'hostProvider'> = {
  getEntity: (s) => s.adcm.hostProvider.hostProvider,
  getDynamicActions: (s, hostProviderId) =>
    s.adcm.hostProvidersDynamicActions.hostProviderDynamicActions[hostProviderId] ?? EMPTY_DYNAMIC_ACTIONS,
  openDialog: openHostProviderDynamicActionDialog,
  getEntityParams: (hostProvider) => ({ hostProvider }),
};
