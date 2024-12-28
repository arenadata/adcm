import Input from './Input';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof Input>;
export default {
  title: 'uikit/Input',
  component: Input,
  argTypes: {
    disabled: {
      description: 'Disabled',
      control: { type: 'boolean' },
    },
    startAdornment: {
      table: {
        disable: true,
      },
    },
    endAdornment: {
      table: {
        disable: true,
      },
    },
    variant: {
      table: {
        disable: true,
      },
    },
    placeholder: {
      control: { type: 'text' },
    },
  },
} as Meta<typeof Input>;

export const EasyInput: Story = {
  args: {
    placeholder: 'Some placeholder',
  },
};
