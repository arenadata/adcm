import ClusterImportCard, {
  ClusterImportEmptyCard,
} from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard';
import { useClusterImportsService } from './useClusterImportsService';
import ClusterImportToolbar from '@pages/cluster/ClusterImport/ClusterImportToolbar/ClusterImportToolbar';
import { LabeledField, Pagination, Select } from '@uikit';

const ClusterImportsService = () => {
  const {
    clusterImports,
    selectedSingleBind,
    selectedImports,
    selectedImportsToggleHandler,
    isValid,
    hasSaveError,
    isLoading,
    onImportHandler,
    paginationParams,
    paginationHandler,
    serviceListOptions,
    serviceId,
    handleServiceChange,
    totalCount,
  } = useClusterImportsService();

  return (
    <>
      <ClusterImportToolbar isDisabled={!isValid} onClick={onImportHandler} hasError={hasSaveError}>
        <LabeledField label="import to" direction="row">
          <Select
            maxHeight={200}
            placeholder="None"
            value={serviceId ?? null}
            onChange={handleServiceChange}
            options={serviceListOptions}
            noneLabel="None"
          />
        </LabeledField>
      </ClusterImportToolbar>
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

export default ClusterImportsService;
