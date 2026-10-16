import type React from 'react';
import { Badge, Icon, TableCell, Tooltip } from '@uikit';
import type { AdcmContractVersion } from '@models/adcm';
import { getContractVersionBadgeStatus } from '@utils/contractVersionUtils';
import { entityContractVersionTooltips } from './EntityVersionCell.constants';
import s from './EntityVersionCell.module.scss';

interface EntityVersionCellProps {
  versionInfo: { contractVersion?: AdcmContractVersion; version: string };
}

const EntityVersionCell: React.FC<EntityVersionCellProps> = ({ versionInfo }) => {
  const contractVersionStatus = versionInfo.contractVersion?.status;
  const tooltip = contractVersionStatus ? entityContractVersionTooltips[contractVersionStatus] : undefined;

  return (
    <TableCell>
      <div className={s.entityVersionCell}>
        <Badge status={getContractVersionBadgeStatus(contractVersionStatus)} truncate title={versionInfo.version}>
          {versionInfo.version}
        </Badge>
        {tooltip && (
          <Tooltip label={tooltip} placement="top">
            <Icon name="g1-info" size={24} className={s.entityVersionCell__icon} />
          </Tooltip>
        )}
      </div>
    </TableCell>
  );
};

export default EntityVersionCell;
