import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import ConfigVersionPanel from '@commonComponents/configuration/ConfigVersionPanel/ConfigVersionPanel';
import type { PaginationParams } from '@models/table';
import type { ConfigVersion, SelectVersionAction } from './ConfigVersionPanel.types';

type Story = StoryObj<typeof ConfigVersionPanel>;
export default {
  title: 'uikit/Common Components/ConfigVersionPanel',
  component: ConfigVersionPanel,
} as Meta<typeof ConfigVersionPanel>;

const paginationParams = {
  perPage: 5,
  pageNumber: 0,
};

const configs = [
  {
    id: 10,
    isCurrent: true,
    creationTime: '2023-09-27T10:29:11.735713Z',
    description: '',
  },
  {
    id: null,
    isCurrent: false,
    creationTime: '',
    description: 'Editing mode',
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

const handleSelectAction = ({ action, configId }: SelectVersionAction) => {
  console.info(action, configId);
};

const handlePageChange = (arg: PaginationParams) => {
  console.info(arg);
};

const ConfigVersionPanelTest: React.FC = () => {
  const [selectedConfigId, setSelectedConfigId] = useState<ConfigVersion['id']>(configs[0].id);
  return (
    <>
      <ConfigVersionPanel
        totalItems={5}
        paginationParams={paginationParams}
        configsVersions={configs}
        onChangePage={handlePageChange}
        onSelectAction={handleSelectAction}
        selectedConfigId={selectedConfigId}
        onSelectConfigVersion={setSelectedConfigId}
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
