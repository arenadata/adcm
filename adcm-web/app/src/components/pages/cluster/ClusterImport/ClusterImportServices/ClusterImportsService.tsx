import ClusterImportCard, {
  ClusterImportEmptyCard,
} from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard';
import { useClusterImportsService } from './useClusterImportsService';
import ClusterImportToolbar from '@pages/cluster/ClusterImport/ClusterImportToolbar/ClusterImportToolbar';
import { LabeledField, Pagination, Select } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';

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

  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { label: 'Import' },
          { label: 'Services' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <>
      <ClusterImportToolbar isDisabled={!isValid} onClick={onImportHandler} hasError={hasSaveError}>
        <LabeledField label="Import to" direction="row">
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
