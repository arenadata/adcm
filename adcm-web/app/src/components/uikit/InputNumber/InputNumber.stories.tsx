import InputNumberComponent from './InputNumber';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof InputNumberComponent>;
export default {
  title: 'uikit/Input',
  component: InputNumberComponent,
  argTypes: {
    disabled: {
      description: 'Disabled',
      control: { type: 'boolean' },
    },
    variant: {
      table: {
        disable: true,
      },
    },
    placeholder: {
      control: { type: 'text' },
    },
    min: {
      description: 'Disabled',
      control: { type: 'number' },
    },
    max: {
      description: 'Disabled',
      control: { type: 'number' },
    },
  },
} as Meta<typeof InputNumberComponent>;

export const InputNumber: Story = {
  args: {
    placeholder: 'Paste number only',
  },
};
