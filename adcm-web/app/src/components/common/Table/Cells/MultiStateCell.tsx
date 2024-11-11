import type { AdcmCluster, AdcmClusterHost, AdcmHost, AdcmHostProvider, AdcmService } from '@models/adcm';
import { ConditionalWrapper, TableCell, Tooltip } from '@uikit';
import React from 'react';

interface MultiStateCellProps {
  entity: AdcmCluster | AdcmClusterHost | AdcmHostProvider | AdcmHost | AdcmService;
}

const MultiStateCell = ({ entity }: MultiStateCellProps) => {
  return (
    <TableCell>
      <ConditionalWrapper
        Component={Tooltip}
        isWrap={!!entity.multiState.length}
        label={entity.multiState?.map((state) => <div key={state}>{state}</div>)}
        placement="top-start"
        closeDelay={100}
      >
        <div>{entity.state}</div>
      </ConditionalWrapper>
    </TableCell>
  );
};

export default MultiStateCell;
