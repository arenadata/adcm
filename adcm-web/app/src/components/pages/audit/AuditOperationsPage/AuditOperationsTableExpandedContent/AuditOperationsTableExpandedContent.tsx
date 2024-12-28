import { Table, TableCell, TableRow } from '@uikit';
import { columns } from './AuditOperationsTableExpandedContent.const';
import type { AdcmAuditOperationObjectChanges } from '@models/adcm';
import { orElseGet } from '@utils/checkUtils';
import type { JSONValue } from '@models/json';

export interface AuditOperationsTableExpandedContentProps {
  objectChanges: AdcmAuditOperationObjectChanges;
}

const prepareValue = (prepValue: JSONValue): string => {
  return orElseGet(prepValue, (value) => {
    if (Array.isArray(value)) {
      return value.map((item) => prepareValue(item)).join(', ');
    }

    if (typeof value === 'object') {
      return JSON.stringify(value);
    }

    return String(value);
  });
};

const AuditOperationsTableExpandedContent = ({ objectChanges }: AuditOperationsTableExpandedContentProps) => {
  if (!objectChanges.previous) return null;

  const keys = Object.keys(objectChanges.previous);

  return (
    <Table columns={columns} variant="quaternary" width="auto">
      {keys.map((key) => (
        <TableRow key={key}>
          <TableCell>{key}</TableCell>
          <TableCell>{prepareValue(objectChanges.previous[key])}</TableCell>
          <TableCell>{prepareValue(objectChanges.current[key])}</TableCell>
        </TableRow>
      ))}
    </Table>
  );
};

export default AuditOperationsTableExpandedContent;
