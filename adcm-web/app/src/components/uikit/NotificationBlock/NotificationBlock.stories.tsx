import type { Meta, StoryObj } from '@storybook/react';
import { Link } from 'react-router-dom';
import NotificationBlock from './NotificationBlock';

type Story = StoryObj<typeof NotificationBlock>;

export default {
  title: 'uikit/NotificationBlock',
  component: NotificationBlock,
} as Meta<typeof NotificationBlock>;

export const Default: Story = {
  render: () => (
    <NotificationBlock>
      You don&apos;t have any clusters yet — create your first cluster to get started.
    </NotificationBlock>
  ),
};

export const WithLink: Story = {
  render: () => (
    <NotificationBlock>
      No services have been installed on this cluster yet. You can install them on the{' '}
      <Link to="/clusters/1/services" className="text-link">
        Services
      </Link>{' '}
      page.
    </NotificationBlock>
  ),
};
