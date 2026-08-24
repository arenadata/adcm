import type { Meta, StoryObj } from '@storybook/react';
import Badge from './Badge';
import type { BadgeStatus } from './Badge.types';

type Story = StoryObj<typeof Badge>;

const statuses: BadgeStatus[] = ['danger', 'warning', 'success', 'info'];

export default {
  title: 'uikit/Badge',
  component: Badge,
  argTypes: {
    status: {
      control: { type: 'select' },
      options: statuses,
    },
    truncate: {
      control: { type: 'boolean' },
    },
    children: {
      control: { type: 'text' },
    },
  },
} as Meta<typeof Badge>;

export const Default: Story = {
  args: {
    status: 'info',
    children: 'Badge',
  },
};

export const AllStatuses: Story = {
  render: () => (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
      <Badge status="danger">12 concerns</Badge>
      <Badge status="warning">Near limit</Badge>
      <Badge status="success">Up</Badge>
      <Badge status="info">Enterprise</Badge>
    </div>
  ),
};

export const Truncated: Story = {
  render: () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: 280 }}>
      <Badge status="info" truncate title="16.3_arenadata6ADPG_2970_b1-adpg16_dev_ts.20260407044102">
        16.3_arenadata6ADPG_2970_b1-adpg16_dev_ts.20260407044102
      </Badge>
      <div style={{ display: 'flex', gap: '8px', minWidth: 0 }}>
        <Badge status="info" truncate title="16.3_arenadata6ADPG_2970_b1-adpg16_dev_ts.20260407044102">
          16.3_arenadata6ADPG_2970_b1-adpg16_dev_ts.20260407044102
        </Badge>
        <Badge status="info">Enterprise</Badge>
      </div>
    </div>
  ),
};
