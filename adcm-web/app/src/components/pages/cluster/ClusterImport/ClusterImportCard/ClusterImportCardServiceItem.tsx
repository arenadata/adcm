import { Checkbox } from '@uikit';
import s from '@pages/cluster/ClusterImport/ClusterImportCard/ClusterImportCard.module.scss';
import type { ClusterImportCardServiceItemProps } from '@pages/cluster/ClusterImport/ClusterImport.types';
import {
  formatServiceToggleData,
  isServiceBlockedBySingleBind,
  isServiceSelected,
} from '@pages/cluster/ClusterImport/ClusterImport.utils';

const ClusterImportCardServiceItem = ({
  service,
  onCheckHandler,
  selectedSingleBind,
  selectedImports,
}: ClusterImportCardServiceItemProps) => {
  const serviceCheckHandler = () => {
    onCheckHandler([formatServiceToggleData(service)]);
  };

  const isSelected = isServiceSelected(service, selectedImports);
  const isDisabled = isServiceBlockedBySingleBind(service, selectedImports, selectedSingleBind);

  return (
    <Checkbox
      label={service.displayName}
      className={s.clusterImportItem__checkbox}
      onChange={serviceCheckHandler}
      disabled={isDisabled}
      checked={isSelected}
    />
  );
};

export default ClusterImportCardServiceItem;
