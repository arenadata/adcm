import type React from 'react';
import { IconButton, Table, TableCell, TableRow } from '@uikit';
import { columns } from './ConfigGroupsTable.constants';
import type { AdcmConfigGroup } from '@models/adcm';
import type { TableProps } from '@uikit/Table/Table';
import { generatePath, Link } from 'react-router-dom';

interface ConfigGroupsTableProps extends Pick<TableProps, 'isLoading' | 'sortParams' | 'onSorting'> {
  configGroups: AdcmConfigGroup[];
  onMapping: (configGroup: AdcmConfigGroup) => void;
  onDelete: (configGroup: AdcmConfigGroup) => void;
  editUrlPattern: string;
}

const ConfigGroupsTable: React.FC<ConfigGroupsTableProps> = ({
  configGroups,
  isLoading,
  sortParams,
  onSorting,
  editUrlPattern,
  onDelete,
  onMapping,
}) => {
  const getHandlerOpenMapping = (configGroup: AdcmConfigGroup) => () => {
    onMapping(configGroup);
  };

  return (
    <Table columns={columns} isLoading={isLoading} sortParams={sortParams} onSorting={onSorting} variant="secondary">
      {configGroups.map((configGroup) => {
        const configGroupUrl = generatePath(editUrlPattern, { configGroupId: configGroup.id });
        return (
          <TableRow key={configGroup.id}>
            <TableCell>
              <Link to={configGroupUrl} className="text-link">
                {configGroup.name}
              </Link>
            </TableCell>
            <TableCell>{configGroup.description}</TableCell>
            <TableCell>
              <span className="text-link" onClick={getHandlerOpenMapping(configGroup)}>
                {configGroup.hosts.length} host{configGroup.hosts.length > 1 ? 's' : ''}
              </span>
            </TableCell>
            <TableCell hasIconOnly align="center">
              <IconButton icon="g1-map" size={32} title="Mapping" onClick={getHandlerOpenMapping(configGroup)} />
              <Link to={configGroupUrl} className="flex-inline">
                <IconButton icon="g1-edit" size={32} title="Edit" />
              </Link>
              <IconButton icon="g1-delete" size={32} title="Delete" onClick={() => onDelete(configGroup)} />
            </TableCell>
          </TableRow>
        );
      })}
    </Table>
  );
};
export default ConfigGroupsTable;
