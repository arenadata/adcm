import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { useParams, useSearchParams } from 'react-router-dom';
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

import type {
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

import type { PaginationParams } from '@models/table';
import { isShowSpinner } from '@uikit/Table/Table.utils';

export const useClusterImportsService = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);
  const [searchParams] = useSearchParams();

  const concernServiceId = Number(searchParams.get('serviceId'));

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
  const { clusterImports, hasSaveError, totalCount } = useStore(({ adcm }) => adcm.clusterImportsService);
  const accessCheckStatus = useStore(({ adcm }) => adcm.clusterImportsService.accessCheckStatus);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.clusterImportsService.loadState));
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
    if (serviceId) {
      dispatch(getClusterServiceImports({ clusterId }));
    } else {
      dispatch(cleanupClusterServiceImports());
    }
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

  const handleServiceChange = useCallback(
    (value: number | null) => {
      dispatch(setFilter({ serviceId: value }));
    },
    [dispatch],
  );

  useEffect(() => {
    if (concernServiceId) {
      handleServiceChange(concernServiceId);
    }
  }, [handleServiceChange, concernServiceId]);

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
    initialImports,
    accessCheckStatus,
  };
};
