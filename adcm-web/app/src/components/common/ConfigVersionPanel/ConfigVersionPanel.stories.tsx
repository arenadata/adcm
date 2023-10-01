import React from 'react';
import { Meta, StoryObj } from '@storybook/react';
import ConfigVersionPanel from '@commonComponents/ConfigVersionPanel/ConfigVersionPanel';
import { PaginationParams } from '@models/table';

type Story = StoryObj<typeof ConfigVersionPanel>;
export default {
  // eslint-disable-next-line spellcheck/spell-checker
  title: 'uikit/Common Components/ConfigVersionPanel',
  component: ConfigVersionPanel,
} as Meta<typeof ConfigVersionPanel>;

const paginationParams = {
  perPage: 5,
  pageNumber: 0,
};

const actions = [
  {
    id: 1,
    displayName: 'Compare',
  },
  {
    id: 2,
    displayName: 'Delete',
  },
];

const configs = [
  {
    id: 10,
    isCurrent: true,
    creationTime: '2023-09-27T10:29:11.735713Z',
    description: '',
  },
  {
    id: 9,
    isCurrent: false,
    creationTime: '2023-09-27T10:29:02.053948Z',
    description: '',
  },
  {
    id: 4,
    isCurrent: false,
    creationTime: '2023-09-27T08:37:29.465944Z',
    description: 'init',
  },
];

const handleSelectAction = () => {
  alert('Click!');
};

const handlePageChange = (arg: PaginationParams) => {
  alert('Page changed!' + JSON.stringify(arg));
};

const handleCellChange = (arg: number) => {
  alert('Cell changed!' + JSON.stringify(arg));
};

const ConfigVersionPanelTest: React.FC = () => {
  return (
    <>
      <ConfigVersionPanel
        paginationParams={paginationParams}
        configCellActionsList={actions}
        configs={configs}
        onChangePage={handlePageChange}
        onSelectCell={handleCellChange}
        onSelectCellAction={handleSelectAction}
      />
    </>
  );
};

export const ConfigVersionPanelExample: Story = {
  render: () => {
    return (
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <ConfigVersionPanelTest />
      </div>
    );
  },
};
