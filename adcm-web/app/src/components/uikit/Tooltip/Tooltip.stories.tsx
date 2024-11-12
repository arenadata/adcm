import type { Meta, StoryObj } from '@storybook/react';
import Tooltip from './Tooltip';
import Button from '@uikit/Button/Button';

type Story = StoryObj<typeof Tooltip>;
export default {
  title: 'uikit/Tooltip',
  component: Tooltip,
} as Meta<typeof Tooltip>;

export const EasyTooltip: Story = {
  args: {
    label: 'Some tooltip text',
    offset: 8,
    placement: 'bottom',
  },
  render: (args) => {
    return (
      <Tooltip {...args}>
        <Button>Some button</Button>
      </Tooltip>
    );
  },
};

export const DisabledButtonTooltip: Story = {
  args: {
    label: 'This button disabled, but tooltip is showing',
    offset: 8,
    placement: 'right',
  },
  render: (args) => {
    return (
      <Tooltip {...args}>
        <span style={{ display: 'inline-flex' }}>
          <Button disabled>Some button</Button>
        </span>
      </Tooltip>
    );
  },
};
