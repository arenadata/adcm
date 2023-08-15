import ClusterImportCard, {
  ClusterImportEmptyCard,
} from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard';
import { useClusterImports } from './useClusterImports';
import ClusterImportToolbar from '@pages/cluster/ClusterImport/ClusterImportToolbar/ClusterImportToolbar';
import { Pagination } from '@uikit';

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
