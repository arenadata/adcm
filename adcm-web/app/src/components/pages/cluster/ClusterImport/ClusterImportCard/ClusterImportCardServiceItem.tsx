import { AdcmClusterImportPayloadType } from '@models/adcm';
import { Checkbox } from '@uikit';
import s from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard.module.scss';
import { ClusterImportCardServiceItemProps } from '@pages/cluster/ClusterImport/ClusterImport.types';

const ClusterImportCardServiceItem = ({
  service,
  onCheckHandler,
  selectedSingleBind,
  selectedImports,
}: ClusterImportCardServiceItemProps) => {
  const serviceCheckHandler = () => {
    onCheckHandler([
      {
        id: service.id,
        type: AdcmClusterImportPayloadType.service,
        name: service.name,
        isMultiBind: service.isMultiBind,
      },
    ]);
  };

  const isServiceSelected = selectedImports.services.has(service.id);
  const isDisabled = !service.isMultiBind && selectedSingleBind.services.has(service.name) && !isServiceSelected;

  return (
    <Checkbox
      key={service.id}
      label={service.displayName}
      className={s.clusterImportItem__checkbox}
      onChange={serviceCheckHandler}
      disabled={isDisabled}
      checked={isServiceSelected}
    />
  );
};

export default ClusterImportCardServiceItem;
