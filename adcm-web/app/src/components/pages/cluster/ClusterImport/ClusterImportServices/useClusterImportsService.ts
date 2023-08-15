import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import {
  getClusterServiceImports,
  saveClusterServiceImports,
  cleanupClusterServiceImports,
} from '@store/adcm/cluster/imports/service/clusterImportsServiceSlice';
import {
  setPaginationParams,
  loadRelatedData,
  cleanupRelatedData,
  setFilter,
  resetFilter,
} from '@store/adcm/cluster/imports/service/clusterImportsServiceFilterSlice';

import {
  ClusterImportsSetGroup,
  SelectedImportHandlerData,
  SelectedImportsGroup,
} from '@pages/cluster/ClusterImport/ClusterImport.types';
import {
  formatToPayloadPostData,
  getIsImportsValid,
  getLoadableData,
  getRequiredImports,
  prepToggleSelectedImportsData,
  prepToggleSelectedSingleBindData,
} from '@pages/cluster/ClusterImport/ClusterImport.utils';

import { PaginationParams } from '@models/table';

export const useClusterImportsService = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const [initialImports, setInitialImports] = useState<SelectedImportsGroup>({
    clusters: new Map(),
    services: new Map(),
  });
  const [selectedImports, setSelectedImports] = useState<SelectedImportsGroup>({
    clusters: new Map(),
    services: new Map(),
  });
  const [selectedSingleBind, setSelectedSingleBind] = useState<ClusterImportsSetGroup>({
    clusters: new Set(),
    services: new Set(),
  });
  const { clusterImports, hasSaveError, isLoading, totalCount } = useStore(({ adcm }) => adcm.clusterImportsService);
  const {
    paginationParams,
    relatedData: { serviceList },
    filter: { serviceId },
  } = useStore(({ adcm }) => adcm.clusterImportsServiceFilter);

  useEffect(() => {
    dispatch(loadRelatedData({ clusterId }));

    return () => {
      dispatch(resetFilter());
      dispatch(cleanupRelatedData());
      dispatch(cleanupClusterServiceImports());
    };
  }, [clusterId, dispatch]);

  useEffect(() => {
    if (serviceId) dispatch(getClusterServiceImports({ clusterId }));
  }, [serviceId, paginationParams, clusterId, dispatch]);

  useEffect(() => {
    const [loadedImports, loadedSingleBind] = getLoadableData(clusterImports);
    setInitialImports(loadedImports);
    setSelectedImports(loadedImports);
    setSelectedSingleBind(loadedSingleBind);
  }, [clusterImports]);

  const requiredImports: ClusterImportsSetGroup = useMemo(() => getRequiredImports(clusterImports), [clusterImports]);

  const isValid = useMemo(
    () => getIsImportsValid(selectedImports, requiredImports, initialImports),
    [selectedImports, requiredImports, initialImports],
  );

  const serviceListOptions = useMemo(
    () =>
      serviceList.map((service) => ({
        value: service.id,
        label: service.displayName,
      })),
    [serviceList],
  );

  const selectedImportsToggleHandler = useCallback((newSelectedImports: SelectedImportHandlerData[]) => {
    setSelectedImports((prevState) => prepToggleSelectedImportsData(prevState, newSelectedImports));
    setSelectedSingleBind((prevState) => prepToggleSelectedSingleBindData(prevState, newSelectedImports));
  }, []);

  const onImportHandler = () => {
    dispatch(
      saveClusterServiceImports({
        clusterId,
        clusterImportsList: formatToPayloadPostData(selectedImports),
      }),
    );
  };

  const paginationHandler = (pageData: PaginationParams) => {
    dispatch(setPaginationParams(pageData));
  };

  const handleServiceChange = (value: number | null) => {
    dispatch(setFilter({ serviceId: value }));
  };

  return {
    clusterImports,
    selectedImports,
    selectedImportsToggleHandler,
    selectedSingleBind,
    isValid,
    onImportHandler,
    hasSaveError,
    isLoading,
    paginationParams,
    paginationHandler,
    serviceId,
    serviceListOptions,
    handleServiceChange,
    totalCount,
  };
};
