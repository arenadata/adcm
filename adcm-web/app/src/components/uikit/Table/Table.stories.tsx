/* eslint-disable spellcheck/spell-checker */
import type { TableProps } from './Table';
import Table from './Table';
import type { Meta, StoryObj } from '@storybook/react';
import type { TableColumn } from '@uikit/Table/Table.types';
import TableRow from '@uikit/Table/TableRow/TableRow';
import TableCell from '@uikit/Table/TableCell/TableCell';
import { orElseGet } from '@utils/checkUtils';
import IconButton from '@uikit/IconButton/IconButton';
import type { ChangeEvent } from 'react';
import React, { useEffect, useMemo, useState } from 'react';
import cn from 'classnames';
import type { SortParams } from '@uikit/types/list.types';
import { getSortingData } from '@utils/localFilteredData';
import Statusable from '@uikit/Statusable/Statusable';
import Checkbox from '@uikit/Checkbox/Checkbox';

type Story = StoryObj<typeof Table>;
export default {
  title: 'uikit/Table',
  component: Table,
  argTypes: {
    sortParams: {
      table: {
        disable: true,
      },
    },
    onSorting: {
      table: {
        disable: true,
      },
    },
    spinner: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof Table>;

const columns = [
  {
    name: 'name',
    label: 'Name',
    isSortable: true,
  },
  {
    name: 'state',
    label: 'State',
  },
  {
    name: 'product',
    label: 'Product',
    isSortable: true,
  },
  {
    name: 'version',
    label: 'Version',
  },
  {
    name: 'description',
    label: 'Description',
  },
  {
    name: 'concerns',
    label: 'Concerns',
    width: '100px',
  },
  {
    name: 'actions',
    label: 'Actions',
    width: '100px',
  },
] as TableColumn[];

const data = [
  {
    id: 1,
    name: 'Quiet Oka1',
    state: 'installed',
    product: 'ADB-z',
    version: '6.22.1',
    description: 'asd',
    concerns: 'Advanced info for tooltips',
  },
  {
    id: 2,
    name: 'Quiet Oka2',
    state: 'installed',
    product: 'ADB-y',
    version: '6.22.1',
    concerns: 'Advanced info for tooltips',
  },
  {
    id: 3,
    name: 'Quiet Oka3',
    state: 'installed',
    product: 'ADB-x',
    version: '6.22.1',
    concerns: 'Advanced info for tooltips',
  },
];

const EasyTableExample: React.FC<TableProps> = (args) => {
  const [sortParams, setSortParams] = useState<SortParams>({
    sortBy: 'name',
    sortDirection: 'asc',
  });
  const [localData, setLocalData] = useState(data);

  useEffect(() => {
    setLocalData(getSortingData(data, sortParams));
  }, [sortParams]);

  const [selectedRows, setSelectedRows] = useState(new Set<number>());
  const getHandleClick = (index: number) => () => {
    setSelectedRows((prev) => {
      if (!prev.has(index)) {
        prev.add(index);
      } else {
        prev.delete(index);
      }

      return new Set([...prev]);
    });
  };

  const handleSorting = (sortParams: SortParams) => {
    args.onSorting?.(sortParams);
    setSortParams(sortParams);
  };

  return (
    <div>
      <Table {...args} columns={columns} sortParams={sortParams} onSorting={handleSorting}>
        {localData.map((entity, index) => (
          <TableRow
            key={entity.id}
            onClick={getHandleClick(index)}
            className={cn({ 'is-selected': selectedRows.has(index) })}
          >
            <TableCell>
              <Statusable status="unknown">
                <a className="text-link" href="/some/url">
                  {entity.name}
                </a>
              </Statusable>
            </TableCell>
            <TableCell>{entity.state}</TableCell>
            <TableCell>{entity.product}</TableCell>
            <TableCell>{entity.version}</TableCell>
            <TableCell>{orElseGet(entity.description)}</TableCell>
            <TableCell hasIconOnly>
              <IconButton icon="g1-info" size={32} />
            </TableCell>
            <TableCell hasIconOnly>
              <IconButton icon="g1-actions" size={32} />
              <IconButton icon="g1-upgrade" size={32} disabled />
              <IconButton icon="g1-delete" size={32} />
            </TableCell>
          </TableRow>
        ))}
      </Table>
    </div>
  );
};

export const EasyTable: Story = {
  args: {
    variant: 'primary',
  },
  render: (args: TableProps) => {
    return <EasyTableExample {...args} />;
  },
};

const CheckedTableExample: React.FC<TableProps> = (args) => {
  const localColumns = [
    {
      isCheckAll: true,
      name: 'checkAll',
    },
    ...columns,
  ];

  const [sortParams, setSortParams] = useState<SortParams>({
    sortBy: 'name',
    sortDirection: 'asc',
  });
  const [localData, setLocalData] = useState(data);

  useEffect(() => {
    setLocalData(getSortingData(data, sortParams));
  }, [sortParams]);

  const [selectedRows, setSelectedRows] = useState(new Set<string>());
  const getHandleSelectedRow = (name: string) => (e: ChangeEvent<HTMLInputElement>) => {
    setSelectedRows((prev) => {
      if (e.target.checked) {
        prev.add(name);
      } else {
        prev.delete(name);
      }

      return new Set([...prev]);
    });
  };

  const handleSorting = (sortParams: SortParams) => {
    args.onSorting?.(sortParams);
    setSortParams(sortParams);
  };

  const toggleSelectedAll = (isAllSelected: boolean) => {
    const list = isAllSelected ? data.map(({ name }) => name) : [];

    setSelectedRows(new Set(list));
  };

  const isAllSelected = useMemo(() => {
    return data.every((item) => selectedRows.has(item.name));
  }, [selectedRows]);

  return (
    <div>
      <Table
        {...args}
        columns={localColumns}
        sortParams={sortParams}
        onSorting={handleSorting}
        isAllSelected={isAllSelected}
        toggleSelectedAll={toggleSelectedAll}
      >
        {localData.map((entity) => (
          <TableRow key={entity.id} className={cn({ 'is-selected': selectedRows.has(entity.name) })}>
            <TableCell>
              <Checkbox checked={selectedRows.has(entity.name)} onChange={getHandleSelectedRow(entity.name)} />
            </TableCell>
            <TableCell>
              <Statusable status="unknown">
                <a className="text-link" href="/some/url">
                  {entity.name}
                </a>
              </Statusable>
            </TableCell>
            <TableCell>{entity.state}</TableCell>
            <TableCell>{entity.product}</TableCell>
            <TableCell>{entity.version}</TableCell>
            <TableCell>{orElseGet(entity.description)}</TableCell>
            <TableCell hasIconOnly>
              <IconButton icon="g1-info" size={32} />
            </TableCell>
            <TableCell hasIconOnly>
              <IconButton icon="g1-actions" size={32} />
              <IconButton icon="g1-upgrade" size={32} disabled />
              <IconButton icon="g1-delete" size={32} />
            </TableCell>
          </TableRow>
        ))}
      </Table>
    </div>
  );
};

export const CheckedTable: Story = {
  args: {
    variant: 'tertiary',
  },
  render: (args: TableProps) => {
    return <CheckedTableExample {...args} />;
  },
};
