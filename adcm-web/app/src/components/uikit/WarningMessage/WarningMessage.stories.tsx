import type { Meta, StoryObj } from '@storybook/react';
import { Button } from '@uikit';
import WarningMessage from '@uikit/WarningMessage/WarningMessage';

type Story = StoryObj<typeof WarningMessage>;
export default {
  title: 'uikit/WarningMessage',
  component: WarningMessage,
} as Meta<typeof WarningMessage>;

export const WarningMessageElement: Story = {
  render: (args) => {
    return (
      <WarningMessage {...args}>
        Warning message <strong>bold text</strong>
      </WarningMessage>
    );
  },
};

export const ErrorMessageElement: Story = {
  args: {
    variant: 'error',
  },
  render: (args) => {
    return (
      <WarningMessage {...args}>
        Error message <strong>bold text</strong>
      </WarningMessage>
    );
  },
};

export const InfoMessageElement: Story = {
  args: {
    variant: 'info',
  },
  render: (args) => {
    return (
      <WarningMessage {...args}>
        Info message <strong>bold text</strong>
      </WarningMessage>
    );
  },
};

export const InfoMessageWithActionElement: Story = {
  args: {
    variant: 'info',
    action: <Button variant="secondary">Don&apos;t show again</Button>,
  },
  render: (args) => {
    return (
      <WarningMessage {...args}>
        Actions execute commands and provider-specific actions on selected hosts. Select hosts with the same provider to
        enable them.
      </WarningMessage>
    );
  },
};
