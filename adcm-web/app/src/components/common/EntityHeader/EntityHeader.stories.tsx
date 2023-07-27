import EntityHeader from './EntityHeader';
import { Meta, StoryObj } from '@storybook/react';
import Statusable from '@uikit/Statusable/Statusable';
import { Button, ButtonGroup } from '@uikit';

type Story = StoryObj<typeof EntityHeader>;

export default {
  // eslint-disable-next-line spellcheck/spell-checker
  title: 'uikit/Common Components/EntityHeader',
  component: EntityHeader,
} as Meta<typeof EntityHeader>;

export const EntityHeaderExample: Story = {
  render: () => {
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
              <Button iconLeft="g1-actions" variant="secondary">
                Actions
              </Button>
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
