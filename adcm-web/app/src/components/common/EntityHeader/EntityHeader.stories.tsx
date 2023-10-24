import EntityHeader from './EntityHeader';
import { Meta, StoryObj } from '@storybook/react';
import Statusable from '@uikit/Statusable/Statusable';
import { Button, ButtonGroup } from '@uikit';
import ActionMenu from '@uikit/ActionMenu/ActionMenu';

type Story = StoryObj<typeof EntityHeader>;

export default {
  // eslint-disable-next-line spellcheck/spell-checker
  title: 'uikit/Common Components/EntityHeader',
  component: EntityHeader,
} as Meta<typeof EntityHeader>;

const actionsOptions = [
  {
    value: 'start',
    label: 'Start Action',
  },
  {
    value: 'stop',
    label: 'Stop Action',
  },
  {
    value: 'pause',
    label: 'Pause Action',
  },
];

export const EntityHeaderExample: Story = {
  render: () => {
    const handleSelectActions = (val: string | null) => {
      window.alert(val);
    };

    return (
      <div style={{ padding: '0 var(--page-padding-h)', color: 'var(--text-)' }}>
        <EntityHeader
          title={
            <Statusable status="done" size="medium">
              Airflow
            </Statusable>
          }
          subtitle="version 1.10.11"
          central={<div>2/2 successful components</div>}
          actions={
            <ButtonGroup>
              <ActionMenu options={actionsOptions} value={null} onChange={handleSelectActions}>
                <Button iconLeft="g1-actions" variant="secondary">
                  Actions
                </Button>
              </ActionMenu>
              <Button iconLeft="g1-delete" variant="secondary">
                Delete
              </Button>
            </ButtonGroup>
          }
        />
      </div>
    );
  },
};
