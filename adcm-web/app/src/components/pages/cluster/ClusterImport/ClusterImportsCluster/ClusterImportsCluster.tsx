import ClusterImportCard, {
  ClusterImportEmptyCard,
} from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard';
import { useClusterImports } from './useClusterImports';
import ClusterImportToolbar from '@pages/cluster/ClusterImport/ClusterImportToolbar/ClusterImportToolbar';
import { Pagination } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

const ClusterImportsCluster = () => {
  const {
    isLoading,
    clusterImports,
    selectedSingleBind,
    selectedImports,
    selectedImportsToggleHandler,
    isValid,
    hasSaveError,
    onImportHandler,
    paginationParams,
    paginationHandler,
    totalCount,
  } = useClusterImports();

  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Import' },
          { label: 'Cluster' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <>
      <ClusterImportToolbar isDisabled={!isValid} onClick={onImportHandler} hasError={hasSaveError} />
      <div>
        {!isLoading &&
          clusterImports.map((item) => (
            <ClusterImportCard
              key={item.cluster.id}
              clusterImport={item}
              selectedSingleBind={selectedSingleBind}
              selectedImports={selectedImports}
              onCheckHandler={selectedImportsToggleHandler}
            />
          ))}
        {!clusterImports.length && <ClusterImportEmptyCard isLoading={isLoading} />}
      </div>
      <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={paginationHandler} />
    </>
  );
};

export default ClusterImportsCluster;
