
import { useState } from 'react';
import Table from '@uikit/Table/Table';
import TableCell from '@uikit/Table/TableCell/TableCell';
import IconButton from '@uikit/IconButton/IconButton';
import { TableColumn } from '@uikit/Table/Table.types';
import ExpandableRowComponent from './ExpandableRow';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof ExpandableRowComponent>;
export default {
  title: 'uikit/Table/ExpandableRow',
  component: ExpandableRowComponent,
  argTypes: {
  },
} as Meta<typeof ExpandableRowComponent>;


const columns = [
  {
    name: 'id',
    label: 'ID',
  },
  {
    name: 'name',
    label: 'Name',
  },
  {
    name: 'state',
    label: 'State',
  },
  {
    name: 'product',
    label: 'Product',
  },
  {
    name: 'version',
    label: 'Version',
  },
  {
    name: 'actions',
    label: 'Actions',
  },
] as TableColumn[];

const data = [
  {
    id: 1,
    name: 'Quiet Oka1',
    state: 'installed',
    product: 'ADB-z',
    version: '6.22.1',
  },
  {
    id: 2,
    name: 'Quiet Oka2',
    state: 'installed',
    product: 'ADB-y',
    version: '6.22.1',
  },
  {
    id: 3,
    name: 'Quiet Oka3',
    state: 'installed',
    product: 'ADB-x',
    version: '6.22.1',
  },
];

const longText = "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book. It has survived not only five centuries, but also the leap into electronic typesetting, remaining essentially unchanged. It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum passages, and more recently with desktop publishing software like Aldus PageMaker including versions of Lorem Ipsum.";

export const ExpandableRow: Story = {
  args: {
  },
  render: (args) => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({
      1: false,
      2: false,
      3: false,
    });

    const handleExpandClick = (id: number) => {
      setExpandableRows({
        ...expandableRows,
        [id]: !expandableRows[id],
      })
    }

    // eslint-disable-next-line @typescript-eslint/no-empty-function
    const handleSorting = () => {};

    return (
      <Table variant='tertiary' {...args} columns={columns} sortParams={{ sortBy: 'id', sortDirection: 'asc'}} onSorting={handleSorting}>
        {data.map((entity) => (
          <ExpandableRowComponent
            key={entity.id}
            colSpan={6}
            isExpanded={expandableRows[entity.id]}
            expandedContent={<div>{longText}</div>}
          >
            <TableCell>{entity.id}</TableCell>
            <TableCell>{entity.name}</TableCell>
            <TableCell>{entity.state}</TableCell>
            <TableCell>{entity.product}</TableCell>
            <TableCell>{entity.version}</TableCell>
            <TableCell hasIconOnly>
              <IconButton icon="g1-info" size={32} onClick={() => handleExpandClick(entity.id)} />
            </TableCell>
          </ExpandableRowComponent>
        ))}
    </Table>)
  },
};
