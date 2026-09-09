import type {
  ClusterImportCardState,
  ClusterImportsSetGroup,
  PrepServicesList,
  SelectedImportHandlerData,
  SelectedImportItem,
  SelectedImportsGroup,
} from '@pages/cluster/ClusterImport/ClusterImport.types';
import type { AdcmClusterImport, AdcmClusterImportPostPayload, AdcmClusterImportService } from '@models/adcm';
import { AdcmClusterImportPayloadType } from '@models/adcm';

export const isServiceSelected = (service: AdcmClusterImportService, selectedImports: SelectedImportsGroup) =>
  selectedImports.services.has(service.id);

export const isServiceBlockedBySingleBind = (
  service: AdcmClusterImportService,
  selectedImports: SelectedImportsGroup,
  selectedSingleBind: ClusterImportsSetGroup,
) =>
  !service.isMultiBind &&
  selectedSingleBind.services.has(service.prototype.name) &&
  !isServiceSelected(service, selectedImports);

export const isAnyServiceBlockedBySingleBind = (
  services: AdcmClusterImportService[],
  selectedImports: SelectedImportsGroup,
  selectedSingleBind: ClusterImportsSetGroup,
) => services.some((service) => isServiceBlockedBySingleBind(service, selectedImports, selectedSingleBind));

export const hasPrototypeSelected = (items: Map<number, SelectedImportItem>, prototypeName: string) => {
  for (const item of items.values()) {
    if (item.prototypeName === prototypeName) return true;
  }

  return false;
};

export const getClusterImportCardState = (
  clusterImport: AdcmClusterImport,
  selectedImports: SelectedImportsGroup,
  selectedSingleBind: ClusterImportsSetGroup,
): ClusterImportCardState => {
  const importServices = clusterImport.importServices;
  const importCluster = clusterImport.importCluster;

  return {
    isAllServicesSelected: !!importServices?.every((service) => isServiceSelected(service, selectedImports)),
    isAnyServiceSelected: !!importServices?.some((service) => isServiceSelected(service, selectedImports)),
    isAllServicesDisabled: importServices
      ? isAnyServiceBlockedBySingleBind(importServices, selectedImports, selectedSingleBind)
      : false,
    requiredServiceImport:
      importServices?.filter(
        (service) => service.isRequired && !hasPrototypeSelected(selectedImports.services, service.prototype.name),
      ) ?? [],
    isClusterImportDisabled:
      !importCluster ||
      (!importCluster.isMultiBind &&
        !selectedImports.clusters.has(clusterImport.cluster.id) &&
        selectedSingleBind.clusters.has(importCluster.prototype.name)),
    isClusterRequired:
      !!importCluster?.isRequired && !hasPrototypeSelected(selectedImports.clusters, importCluster.prototype.name),
    isClusterSelected: !!(importCluster && selectedImports.clusters.has(clusterImport.cluster.id)),
  };
};

export const getCheckServiceList = ({ services, selectedImports, selectedSingleBind }: PrepServicesList) =>
  formatForSelectedToggleHandlerData(
    services.filter(
      (service) =>
        !isServiceSelected(service, selectedImports) &&
        !isServiceBlockedBySingleBind(service, selectedImports, selectedSingleBind),
    ),
  );

export const getUncheckServiceList = ({ services, selectedImports }: PrepServicesList) =>
  formatForSelectedToggleHandlerData(services.filter((service) => isServiceSelected(service, selectedImports)));

export const formatServiceToggleData = (service: AdcmClusterImportService): SelectedImportHandlerData => ({
  id: service.id,
  type: AdcmClusterImportPayloadType.Service,
  isMultiBind: service.isMultiBind,
  prototypeName: service.prototype.name,
});

export const formatForSelectedToggleHandlerData = (services: AdcmClusterImportService[]) =>
  services.map(formatServiceToggleData);

export const getRequiredImports = (clusterImports: AdcmClusterImport[]): ClusterImportsSetGroup => {
  const importsSet: ClusterImportsSetGroup = {
    clusters: new Set([]),
    services: new Set([]),
  };

  clusterImports.forEach((item) => {
    if (item.importCluster?.isRequired) {
      importsSet.clusters.add(item.importCluster.prototype.name);
    }

    item.importServices?.forEach((service) => {
      if (service.isRequired) importsSet.services.add(service.prototype.name);
    });
  });

  return importsSet;
};

export const getIsImportsValid = (
  selectedImports: SelectedImportsGroup,
  requiredImports: ClusterImportsSetGroup,
  initialImports: SelectedImportsGroup,
) => {
  const isNothingChanged = isImportsEqual(selectedImports, initialImports);

  if (isNothingChanged) return false;

  const selectedClustersName = [...selectedImports.clusters.values()].map((value) => value.prototypeName);
  const selectedServicesName = [...selectedImports.services.values()].map((value) => value.prototypeName);

  const isRequiredClustersSelected = [...requiredImports.clusters].every((cluster) =>
    selectedClustersName.includes(cluster),
  );

  const isRequiredServicesSelected = [...requiredImports.services].every((service) =>
    selectedServicesName.includes(service),
  );

  return isRequiredClustersSelected && isRequiredServicesSelected;
};

const isImportsEqual = (currentImports: SelectedImportsGroup, initialImports: SelectedImportsGroup) => {
  if (
    currentImports.clusters.size !== initialImports.clusters.size ||
    currentImports.services.size !== initialImports.services.size
  ) {
    return false;
  }

  const isClustersEqual = [...initialImports.clusters.keys()].every((clusterId) =>
    currentImports.clusters.has(clusterId),
  );

  const isServicesEqual = [...initialImports.services.keys()].every((serviceId) =>
    currentImports.services.has(serviceId),
  );

  return isClustersEqual && isServicesEqual;
};

export const getLoadableData = (
  clusterImports: AdcmClusterImport[],
): [loadedImports: SelectedImportsGroup, loadedBinds: ClusterImportsSetGroup] => {
  const loadedImports: SelectedImportsGroup = {
    clusters: new Map(),
    services: new Map(),
  };

  const loadedSingleBind: ClusterImportsSetGroup = {
    clusters: new Set(),
    services: new Set(),
  };

  clusterImports.forEach((clusterImport) => {
    if (clusterImport.binds.length === 0) return;

    clusterImport.binds.forEach((bind) => {
      if (bind.source.type === AdcmClusterImportPayloadType.Service) {
        if (!clusterImport.importServices) return;

        const foundService = clusterImport.importServices.find((service) => service.id === bind.source.id);
        if (!foundService || loadedImports.services.has(foundService.id)) return;

        loadedImports.services.set(foundService.id, {
          id: foundService.id,
          type: AdcmClusterImportPayloadType.Service,
          prototypeName: foundService.prototype.name,
        });

        if (!foundService.isMultiBind) {
          loadedSingleBind.services.add(foundService.prototype.name);
        }
      } else {
        loadedImports.clusters.set(clusterImport.cluster.id, {
          id: clusterImport.cluster.id,
          type: AdcmClusterImportPayloadType.Cluster,
          prototypeName: clusterImport.importCluster?.prototype.name || '',
        });

        if (clusterImport.importCluster && !clusterImport.importCluster.isMultiBind) {
          loadedSingleBind.clusters.add(clusterImport.importCluster.prototype.name);
        }
      }
    });
  });

  return [loadedImports, loadedSingleBind];
};

export const formatToPayloadPostData = (selectedImports: SelectedImportsGroup) => {
  const clusterImportsList: AdcmClusterImportPostPayload[] = [
    ...selectedImports.clusters.values(),
    ...selectedImports.services.values(),
  ].map((item) => ({ source: { id: item.id, type: item.type } }));

  return clusterImportsList;
};

export const prepToggleSelectedSingleBindData = (
  singleBindList: ClusterImportsSetGroup,
  selectedImports: SelectedImportHandlerData[],
): ClusterImportsSetGroup => {
  const curSelectedMultiBind = {
    clusters: new Set(singleBindList.clusters),
    services: new Set(singleBindList.services),
  };

  selectedImports.forEach(({ type, prototypeName, isMultiBind }) => {
    const keyName = type === AdcmClusterImportPayloadType.Cluster ? 'clusters' : 'services';

    if (isMultiBind) return;

    if (curSelectedMultiBind[keyName].has(prototypeName)) {
      curSelectedMultiBind[keyName].delete(prototypeName);
    } else {
      curSelectedMultiBind[keyName].add(prototypeName);
    }
  });

  return curSelectedMultiBind;
};

export const prepToggleSelectedImportsData = (
  selectedData: SelectedImportsGroup,
  newSelectedData: SelectedImportHandlerData[],
): SelectedImportsGroup => {
  const curItems = {
    clusters: new Map(selectedData.clusters),
    services: new Map(selectedData.services),
  };

  newSelectedData.forEach(({ id, type, prototypeName }) => {
    const keyName = type === AdcmClusterImportPayloadType.Cluster ? 'clusters' : 'services';
    if (curItems[keyName].has(id)) {
      curItems[keyName].delete(id);
    } else {
      curItems[keyName].set(id, { id, type, prototypeName });
    }
  });

  return curItems;
};
