import ClusterImportCard, {
  ClusterImportEmptyCard,
  ClusterImportLoading,
} from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard';
import { useClusterImportsService } from './useClusterImportsService';
import ClusterImportToolbar from '@pages/cluster/ClusterImport/ClusterImportToolbar/ClusterImportToolbar';
import { LabeledField, Pagination, Select } from '@uikit';
import { useDispatch, useStore } from '@hooks';
import { useEffect } from 'react';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import PermissionsChecker from '@commonComponents/PermissionsChecker/PermissionsChecker';
import s from './ClusterImportsService.module.scss';

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
    initialImports,
    accessCheckStatus,
  } = useClusterImportsService();

  const dispatch = useDispatch();

  const cluster = useStore(({ adcm }) => adcm.cluster.cluster);

  useEffect(() => {
    if (cluster) {
      dispatch(
        setBreadcrumbs([
          { href: '/clusters', label: 'Clusters' },
          { href: `/clusters/${cluster.id}`, label: cluster.name },
          { href: `/clusters/${cluster.id}/import`, label: 'Import' },
          { label: 'Services' },
        ]),
      );
    }
  }, [cluster, dispatch]);

  return (
    <div className={s.clusterImportToolbarWrapper}>
      <ClusterImportToolbar
        isDisabled={!isValid}
        onClick={onImportHandler}
        hasError={hasSaveError}
        isImportPresent={initialImports.services.size > 0 || initialImports.clusters.size > 0}
      >
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
      <PermissionsChecker requestState={accessCheckStatus}>
        {isLoading && <ClusterImportLoading />}
        {!isLoading &&
          (clusterImports.length > 0 ? (
            clusterImports.map((item) => (
              <ClusterImportCard
                key={item.cluster.id}
                dataTest={`serviceTab_cluster-${item.cluster.id}`}
                clusterImport={item}
                selectedSingleBind={selectedSingleBind}
                selectedImports={selectedImports}
                onCheckHandler={selectedImportsToggleHandler}
              />
            ))
          ) : (
            <ClusterImportEmptyCard />
          ))}
        <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={paginationHandler} />
      </PermissionsChecker>
    </div>
  );
};

export default ClusterImportsService;
