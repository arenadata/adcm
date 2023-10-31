import { Meta, StoryObj } from '@storybook/react';
import Checkbox from './Checkbox';

type Story = StoryObj<typeof Checkbox>;
export default {
  title: 'uikit/Checkbox',
  component: Checkbox,
  argTypes: {
    disabled: {
      description: 'Disabled',
      defaultValue: false,
    },
    required: {
      description: 'Required',
      defaultValue: false,
      control: 'boolean',
    },
  },
} as Meta<typeof Checkbox>;

export const Checkboxes: Story = {
  args: {
    disabled: false,
    label: 'Label text',
  },
  render: (args) => {
    return <Checkbox {...args} />;
  },
};
