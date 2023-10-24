import {
  ClusterImportsSetGroup,
  PrepServicesList,
  SelectedImportHandlerData,
  SelectedImportItem,
  SelectedImportsGroup,
} from '@pages/cluster/ClusterImport/ClusterImport.types';
import {
  AdcmClusterImport,
  AdcmClusterImportPayloadType,
  AdcmClusterImportPostPayload,
  AdcmClusterImportService,
} from '@models/adcm';

export const getCheckServiceList = ({ services, selectedImports, selectedSingleBind }: PrepServicesList) =>
  formatForSelectedToggleHandlerData(
    services.filter((service) => {
      if (selectedImports.services.has(service.id)) return false;
      return service.isMultiBind || !selectedSingleBind.services.has(service.name);
    }),
  );

export const getUncheckServiceList = ({ services, selectedImports }: PrepServicesList) =>
  formatForSelectedToggleHandlerData(services.filter((service) => selectedImports.services.has(service.id)));

export const formatForSelectedToggleHandlerData = (services: AdcmClusterImportService[]) =>
  services.map((service) => ({
    id: service.id,
    type: AdcmClusterImportPayloadType.Service,
    name: service.name,
    isMultiBind: service.isMultiBind,
  }));

export const getRequiredImports = (clusterImports: AdcmClusterImport[]): ClusterImportsSetGroup => {
  const importsSet: ClusterImportsSetGroup = {
    clusters: new Set([]),
    services: new Set([]),
  };

  clusterImports.forEach((item) => {
    if (item.importCluster?.isRequired) {
      importsSet.clusters.add(item.cluster.name);
    }

    item.importServices?.forEach((service) => {
      if (service.isRequired) importsSet.services.add(service.name);
    });
  });

  return importsSet;
};

export const getIsImportsValid = (
  selectedImports: SelectedImportsGroup,
  requiredImports: ClusterImportsSetGroup,
  initialImports: SelectedImportsGroup,
) => {
  const isOneSelected = selectedImports.services.size > 0 || selectedImports.clusters.size > 0;
  if (!isOneSelected) return false;

  const selectedClustersName = [...selectedImports.clusters.values()].map((value) => value.name);
  const selectedServicesName = [...selectedImports.services.values()].map((value) => value.name);

  const isRequiredClustersSelected = [...requiredImports.clusters].every((cluster) =>
    selectedClustersName.includes(cluster),
  );

  const isRequiredServicesSelected = [...requiredImports.services].every((service) =>
    selectedServicesName.includes(service),
  );

  const isNothingChanged = isImportsEqual(selectedImports, initialImports);

  return isRequiredClustersSelected && isRequiredServicesSelected && !isNothingChanged;
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
          name: foundService.name,
        });

        if (!foundService.isMultiBind) {
          loadedSingleBind.services.add(foundService.name);
        }
      } else {
        loadedImports.clusters.set(clusterImport.cluster.id, {
          id: clusterImport.cluster.id,
          type: AdcmClusterImportPayloadType.Cluster,
          name: clusterImport.cluster.name,
        });

        if (!clusterImport.importCluster?.isMultiBind) {
          loadedSingleBind.clusters.add(clusterImport.cluster.name);
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

  selectedImports.forEach(({ type, name, isMultiBind }) => {
    const keyName = type === AdcmClusterImportPayloadType.Cluster ? 'clusters' : 'services';

    if (isMultiBind) return;

    if (curSelectedMultiBind[keyName].has(name)) {
      curSelectedMultiBind[keyName].delete(name);
    } else {
      curSelectedMultiBind[keyName].add(name);
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

  newSelectedData.forEach(({ id, type, name }) => {
    const keyName = type === AdcmClusterImportPayloadType.Cluster ? 'clusters' : 'services';
    if (curItems[keyName].has(id)) {
      curItems[keyName].delete(id);
    } else {
      curItems[keyName].set(id, { id, type, name });
    }
  });

  return curItems;
};

export const isItemSelected = (itemsArray: SelectedImportItem[], name: string): boolean => {
  return !!itemsArray.find((item) => item.name === name);
};
