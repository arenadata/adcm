import React, { useState } from 'react';
import type { SwitchProps } from './Switch';
import Switch from './Switch';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof Switch>;

export default {
  title: 'uikit/Switch',
  component: Switch,
  argTypes: {
    disabled: {
      description: 'Disabled',
      control: { type: 'boolean' },
    },
    size: {
      defaultValue: 'medium',
      options: ['medium', 'small'],
      control: { type: 'radio' },
    },
    variant: {
      defaultValue: 'green',
      options: ['green', 'blue'],
      control: { type: 'radio' },
    },
  },
} as Meta<typeof Switch>;

const SwitchWithHooks = ({ ...args }: Partial<SwitchProps>) => {
  const [checked, setChecked] = useState(false);

  const handleChangeCheckedBox = (event: React.ChangeEvent<HTMLInputElement>) => {
    setChecked(event.target.checked);
  };

  return (
    <Switch
      isToggled={checked}
      onChange={handleChangeCheckedBox}
      size={args.size}
      disabled={args.disabled}
      variant={args.variant}
    />
  );
};

export const SwitchStory: Story = {
  args: {
    size: 'medium',
    variant: 'green',
    disabled: false,
  },
  render: ({ ...args }) => {
    return <SwitchWithHooks {...args} />;
  },
};
