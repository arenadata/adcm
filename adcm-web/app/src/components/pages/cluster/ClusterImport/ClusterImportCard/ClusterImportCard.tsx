import type React from 'react';
import { Checkbox, Statusable, Spinner } from '@uikit';
import s from './ClusterImportCard.module.scss';
import cn from 'classnames';
import type { AdcmClusterImport } from '@models/adcm';
import { AdcmClusterImportPayloadType, AdcmClusterStatus } from '@models/adcm';
import ClusterImportCardServiceItem from './ClusterImportCardServiceItem';
import type {
  ClusterImportsSetGroup,
  SelectedImportHandlerData,
  SelectedImportsGroup,
} from '@pages/cluster/ClusterImport/ClusterImport.types';
import {
  getCheckServiceList,
  getClusterImportCardState,
  getUncheckServiceList,
} from '@pages/cluster/ClusterImport/ClusterImport.utils';

export interface ClusterImportCardProps {
  clusterImport: AdcmClusterImport;
  selectedSingleBind: ClusterImportsSetGroup;
  selectedImports: SelectedImportsGroup;
  dataTest: string;
  onCheckHandler: (selectedImport: SelectedImportHandlerData[]) => void;
}

export const ClusterImportLoading = () => {
  return (
    <div className={cn(s.clusterImportItem, s.clusterImportItem_empty)}>
      <Spinner />
    </div>
  );
};

export const ClusterImportEmptyCard = () => {
  return (
    <div className={cn(s.clusterImportItem, s.clusterImportItem_empty)} data-test="no-imports">
      No data
    </div>
  );
};

const ClusterImportCard = ({
  clusterImport,
  onCheckHandler,
  selectedSingleBind,
  selectedImports,
  dataTest,
}: ClusterImportCardProps) => {
  const {
    isAllServicesSelected,
    isAnyServiceSelected,
    isAllServicesDisabled,
    requiredServiceImport,
    isClusterImportDisabled,
    isClusterRequired,
    isClusterSelected,
  } = getClusterImportCardState(clusterImport, selectedImports, selectedSingleBind);

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
    <div className={clusterImportItemClasses} data-test={dataTest}>
      <div className={s.clusterImportItem__block}>
        <Statusable
          status={clusterImport.cluster.status === AdcmClusterStatus.Up ? 'done' : 'unknown'}
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
  );
};

export default ClusterImportCard;
