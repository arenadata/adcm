import React from 'react';
import { Table, TableCell, TableRow } from '@uikit';
import { columns } from './AuditOperationsTableExpandedContent.const';
import { AdcmAuditOperationObjectChanges } from '@models/adcm';
import { orElseGet } from '@utils/checkUtils';

export interface AuditOperationsTableExpandedContentProps {
  objectChanges: AdcmAuditOperationObjectChanges;
}

const AuditOperationsTableExpandedContent = ({ objectChanges }: AuditOperationsTableExpandedContentProps) => {
  if (!objectChanges.previous) return null;

  const keys = Object.keys(objectChanges.previous);

  return (
    <Table columns={columns} variant="quaternary" width="auto">
      {keys.map((key) => (
        <TableRow key={key}>
          <TableCell>{key}</TableCell>
          <TableCell>{orElseGet(objectChanges.previous[key])}</TableCell>
          <TableCell>{orElseGet(objectChanges.current[key])}</TableCell>
        </TableRow>
      ))}
    </Table>
  );
};

export default AuditOperationsTableExpandedContent;
