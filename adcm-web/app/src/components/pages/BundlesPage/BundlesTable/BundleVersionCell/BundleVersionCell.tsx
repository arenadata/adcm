import type React from 'react';
import { Badge, Icon, TableCell, Tooltip } from '@uikit';
import { AdcmContractVersionStatus, type AdcmBundle } from '@models/adcm';
import { bundleContractVersionBadgeStatuses, bundleContractVersionTooltips } from '../BundlesTable.constants';
import s from './BundleVersionCell.module.scss';

interface BundleVersionCellProps {
  bundle: AdcmBundle;
}

const BundleVersionCell: React.FC<BundleVersionCellProps> = ({ bundle }) => {
  const contractVersionStatus = bundle.contractVersion?.status;
  const tooltip = contractVersionStatus ? bundleContractVersionTooltips[contractVersionStatus] : undefined;

  return (
    <TableCell>
      <div className={s.bundleVersionCell}>
        <Badge
          status={bundleContractVersionBadgeStatuses[contractVersionStatus ?? AdcmContractVersionStatus.Supported]}
          truncate
          title={bundle.version}
        >
          {bundle.version}
        </Badge>
        {tooltip && (
          <Tooltip label={tooltip} placement="top">
            <Icon name="g1-info" size={24} className={s.bundleVersionCell__icon} />
          </Tooltip>
        )}
      </div>
    </TableCell>
  );
};

export default BundleVersionCell;
