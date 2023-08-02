import React, { useState } from 'react';
import { useDispatch, useStore } from '@hooks';
import { columns } from '@pages/audit/AuditOperationsPage/AuditOperationsTable/AuditOperations.constants';
import { Button, Table, TableCell, ExpandableRowComponent } from '@uikit';
import { setSortParams } from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import { SortParams } from '@models/table';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import AuditOperationsTableExpandedContent from '@pages/audit/AuditOperationsPage/AuditOperationsTableExpandedContent/AuditOperationsTableExpandedContent';
import { orElseGet } from '@utils/checkUtils';

const AuditOperationsTable = () => {
  const dispatch = useDispatch();

  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});

  const auditOperations = useStore(({ adcm }) => adcm.auditOperations.auditOperations);
  const isLoading = useStore(({ adcm }) => adcm.auditOperations.isLoading);
  const sortParams = useStore(({ adcm }) => adcm.auditOperationsTable.sortParams);

  const handleExpandClick = (id: number) => {
    setExpandableRows({
      ...expandableRows,
      [id]: expandableRows[id] === undefined ? true : !expandableRows[id],
    });
  };

  const handleSorting = (sortParams: SortParams) => {
    dispatch(setSortParams(sortParams));
  };

  return (
    <Table variant="tertiary" isLoading={isLoading} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
      {auditOperations.map((auditOperation) => (
        <ExpandableRowComponent
          key={auditOperation.id}
          colSpan={columns.length}
          isExpanded={expandableRows[auditOperation.id] || false}
          expandedContent={<AuditOperationsTableExpandedContent objectChanges={auditOperation.objectChanges} />}
        >
          <TableCell>{orElseGet(auditOperation.object?.type)}</TableCell>
          <TableCell>{orElseGet(auditOperation.object?.name)}</TableCell>
          <TableCell>{orElseGet(auditOperation.name)}</TableCell>
          <TableCell>{orElseGet(auditOperation.type)}</TableCell>
          <TableCell>{orElseGet(auditOperation.result)}</TableCell>
          <DateTimeCell value={orElseGet(auditOperation.time)} />
          <TableCell>{orElseGet(auditOperation.user?.name)}</TableCell>
          <TableCell>
            <Button
              className={expandableRows[auditOperation.id] ? 'is-active' : ''}
              variant="secondary"
              iconLeft="dots"
              onClick={() => handleExpandClick(auditOperation.id)}
              disabled={!auditOperation.objectChanges?.previous}
            />
          </TableCell>
        </ExpandableRowComponent>
      ))}
    </Table>
  );
};

export default AuditOperationsTable;
