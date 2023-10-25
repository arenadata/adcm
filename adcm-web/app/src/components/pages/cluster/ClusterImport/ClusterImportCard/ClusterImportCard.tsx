import React from 'react';
import { Checkbox, Statusable, Spinner } from '@uikit';
import s from './ClusterImportCard.module.scss';
import cn from 'classnames';
import { AdcmClusterImport, AdcmClusterImportPayloadType } from '@models/adcm';
import ClusterImportCardServiceItem from './ClusterImportCardServiceItem';
import {
  ClusterImportsSetGroup,
  SelectedImportHandlerData,
  SelectedImportsGroup,
} from '@pages/cluster/ClusterImport/ClusterImport.types';
import {
  getCheckServiceList,
  getUncheckServiceList,
  isItemSelected,
} from '@pages/cluster/ClusterImport/ClusterImport.utils';

export interface ClusterImportCardProps {
  clusterImport: AdcmClusterImport;
  selectedSingleBind: ClusterImportsSetGroup;
  selectedImports: SelectedImportsGroup;
  onCheckHandler: (selectedImport: SelectedImportHandlerData[]) => void;
}

export interface ClusterImportCardEmptyProps {
  isLoading: boolean;
}

export const ClusterImportEmptyCard = ({ isLoading }: ClusterImportCardEmptyProps) => {
  return (
    <div className={cn(s.clusterImportItem, s.clusterImportItem_empty)}>{isLoading ? <Spinner /> : 'No data'}</div>
  );
};

const ClusterImportCard = ({
  clusterImport,
  onCheckHandler,
  selectedSingleBind,
  selectedImports,
}: ClusterImportCardProps) => {
  // Some services can be "isMultiBind = false", and already selected in another cluster, such services we count here as selected
  const isAllServicesSelected = clusterImport.importServices?.every(
    (service) =>
      selectedImports.services.has(service.id) ||
      (!service.isMultiBind && selectedSingleBind.services.has(service.prototype.name)),
  );

  const isAnyServiceSelected = clusterImport.importServices?.some((service) =>
    selectedImports.services.has(service.id),
  );

  // Disable "Select All" checkbox if all cluster service are "isMultiBind = false" and they already selected in another clusters
  const isAllServicesDisabled = clusterImport.importServices?.every(
    (service) => selectedSingleBind.services.has(service.prototype.name) && !selectedImports.services.has(service.id),
  );

  // Need to show notification if service required for import, and it is not already selected in current or any another clusters
  const requiredServiceImport =
    clusterImport.importServices?.filter(
      (service) =>
        service.isRequired && !isItemSelected([...selectedImports.services.values()], service.prototype.name),
    ) || [];

  // Disable if cluster "isMultiBind = false" and such cluster already selected and if selected cluster with same name is not current cluster;
  const isClusterImportDisabled =
    !clusterImport.importCluster ||
    (!clusterImport.importCluster.isMultiBind &&
      !selectedImports.clusters.has(clusterImport.cluster.id) &&
      selectedSingleBind.clusters.has(clusterImport.importCluster.prototype.name));

  // If cluster required for import and there is not selected cluster with same name
  const isClusterRequired =
    clusterImport.importCluster?.isRequired &&
    isItemSelected([...selectedImports.clusters.values()], clusterImport.importCluster.prototype.name);

  const isClusterSelected = !!(clusterImport.importCluster && selectedImports.clusters.has(clusterImport.cluster.id));
  const clusterCheckHandler = () => {
    if (!clusterImport.importCluster) return;

    onCheckHandler([
      {
        id: clusterImport.importCluster.id,
        type: AdcmClusterImportPayloadType.Cluster,
        prototypeName: clusterImport.importCluster.prototype.name,
        isMultiBind: clusterImport.importCluster.isMultiBind,
      },
    ]);
  };

  const allServicesCheckHandler = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!clusterImport.importServices) return;
    const listProps = { services: clusterImport.importServices, selectedImports, selectedSingleBind };

    const prepList = event.target.checked ? getCheckServiceList(listProps) : getUncheckServiceList(listProps);
    onCheckHandler(prepList);
  };

  const clusterImportItemClasses = cn(s.clusterImportItem, {
    [s.clusterImportItem_active]: isAnyServiceSelected,
    [s.clusterImportItem_require]: requiredServiceImport.length > 0,
  });

  return (
    <>
      <div className={clusterImportItemClasses}>
        <div className={s.clusterImportItem__block}>
          <Statusable
            status={clusterImport.cluster.status === 'up' ? 'running' : 'unknown'}
            size="medium"
            className={s.clusterImportItem__title}
          >
            {clusterImport.cluster.name}
          </Statusable>
          {isClusterRequired && (
            <div className={s.clusterImportItem__requireBlock}>Cluster configuration import is required</div>
          )}
          {requiredServiceImport.map((service) => (
            <div key={service.id} className={s.clusterImportItem__requireBlock}>
              Import of {service.displayName} is required
            </div>
          ))}
        </div>
        <div className={s.clusterImportItem__block}>
          {clusterImport.importCluster && (
            <Checkbox
              label="Cluster configuration"
              checked={isClusterSelected}
              onChange={clusterCheckHandler}
              disabled={isClusterImportDisabled}
            />
          )}
        </div>
        <div className={s.clusterImportItem__block}>
          {clusterImport.importServices && (
            <>
              <Checkbox
                label="All Services"
                onChange={allServicesCheckHandler}
                checked={isAllServicesSelected}
                disabled={isAllServicesDisabled}
              />
              {clusterImport.importServices.map((service) => (
                <ClusterImportCardServiceItem
                  key={service.id}
                  service={service}
                  selectedSingleBind={selectedSingleBind}
                  selectedImports={selectedImports}
                  onCheckHandler={onCheckHandler}
                />
              ))}
            </>
          )}
        </div>
      </div>
    </>
  );
};

export default ClusterImportCard;
