import type { Meta, StoryObj } from '@storybook/react';
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
