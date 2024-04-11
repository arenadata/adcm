import { useCallback, useEffect, useMemo, useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { useParams } from 'react-router-dom';
import {
  getClusterImports,
  saveClusterImports,
  cleanupClusterImports,
} from '@store/adcm/cluster/imports/cluster/clusterImportsSlice';
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
import { setPaginationParams } from '@store/adcm/cluster/imports/cluster/clusterImportsFilterSlice';
import { PaginationParams } from '@models/table';
import { isShowSpinner } from '@uikit/Table/Table.utils';

export const useClusterImports = () => {
  const dispatch = useDispatch();
  const { clusterId: clusterIdFromUrl } = useParams();
  const clusterId = Number(clusterIdFromUrl);

  const [initialSelected, setInitialSelected] = useState<SelectedImportsGroup>({
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
  const { clusterImports, hasSaveError, totalCount } = useStore(({ adcm }) => adcm.clusterImports);
  const isLoading = useStore((s) => isShowSpinner(s.adcm.clusterImports.loadState));
  const accessCheckStatus = useStore(({ adcm }) => adcm.clusterImports.accessCheckStatus);
  const { paginationParams } = useStore(({ adcm }) => adcm.clusterImportsFilter);

  useEffect(() => {
    dispatch(getClusterImports({ clusterId }));

    return () => {
      dispatch(cleanupClusterImports());
    };
  }, [clusterId, dispatch, paginationParams]);

  const requiredImports: ClusterImportsSetGroup = useMemo(() => getRequiredImports(clusterImports), [clusterImports]);

  const isValid = useMemo(
    () => getIsImportsValid(selectedImports, requiredImports, initialSelected),
    [selectedImports, requiredImports, initialSelected],
  );

  const selectedImportsToggleHandler = useCallback((newSelectedImports: SelectedImportHandlerData[]) => {
    setSelectedImports((prevState) => prepToggleSelectedImportsData(prevState, newSelectedImports));
    setSelectedSingleBind((prevState) => prepToggleSelectedSingleBindData(prevState, newSelectedImports));
  }, []);

  useEffect(() => {
    const [loadedImports, loadedSingleBind] = getLoadableData(clusterImports);

    setInitialSelected(loadedImports);
    setSelectedImports(loadedImports);
    setSelectedSingleBind(loadedSingleBind);
  }, [clusterImports]);

  const onImportHandler = () => {
    dispatch(
      saveClusterImports({
        clusterId,
        clusterImportsList: formatToPayloadPostData(selectedImports),
      }),
    );
  };

  const paginationHandler = (pageData: PaginationParams) => {
    dispatch(setPaginationParams(pageData));
  };

  return {
    clusterImports,
    selectedImports,
    selectedImportsToggleHandler,
    selectedSingleBind,
    initialSelected,
    isValid,
    onImportHandler,
    hasSaveError,
    isLoading,
    paginationParams,
    paginationHandler,
    totalCount,
    accessCheckStatus,
  };
};
