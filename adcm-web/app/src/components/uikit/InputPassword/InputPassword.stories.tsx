import InputPasswordComponent from './InputPassword';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof InputPasswordComponent>;
export default {
  title: 'uikit/Input',
  component: InputPasswordComponent,
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
  },
} as Meta<typeof InputPasswordComponent>;

export const InputPassword: Story = {
  args: {
    placeholder: 'Password...',
  },
};
