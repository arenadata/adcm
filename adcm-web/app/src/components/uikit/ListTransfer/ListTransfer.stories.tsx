import ListTransfer from './ListTransfer';
import { Meta, StoryObj } from '@storybook/react';
import { useState } from 'react';
import { ListTransferItem } from '@uikit/ListTransfer/ListTransfer.types';

type Story = StoryObj<typeof ListTransfer>;
export default {
  title: 'uikit/ListTransfer',
  component: ListTransfer,
  argTypes: {},
} as Meta<typeof ListTransfer>;

export const EasyListTransfer: Story = {
  args: {},
  render: () => <ListTransferExample />,
};

const fullItemsList = [
  { key: 1, label: 'Record 01' },
  { key: 2, label: 'Record 02' },
  { key: 3, label: 'Record 03' },
  { key: 4, label: 'Record 04' },
  { key: 5, label: 'Record 05' },
  { key: 6, label: 'Record 06' },
  { key: 7, label: 'Record 07' },
  { key: 8, label: 'Record 08' },
  { key: 9, label: 'Record 09' },
  { key: 10, label: 'Record 10' },
  { key: 11, label: 'Record 11' },
];

const ListTransferExample = () => {
  const [destKeys, setDestKeys] = useState<Set<ListTransferItem['key']>>(new Set());

  return (
    <ListTransfer
      srcList={fullItemsList}
      destKeys={destKeys}
      onChangeDest={setDestKeys}
      srcOptions={{
        actionButtonLabel: 'Transfer selected',
        title: 'Primary',
      }}
      destOptions={{
        actionButtonLabel: 'Transfer selected',
        title: 'Secondary',
      }}
    />
  );
};
