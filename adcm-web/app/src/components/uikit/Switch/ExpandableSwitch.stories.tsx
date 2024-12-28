import type React from 'react';
import { useState } from 'react';
import type { ExpandableSwitchProps } from './ExpandableSwitch';
import ExpandableSwitch from './ExpandableSwitch';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof ExpandableSwitch>;

export default {
  title: 'uikit/Switch',
  component: ExpandableSwitch,
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
} as Meta<typeof ExpandableSwitch>;

const SwitchWithHooks = ({ ...args }: Partial<ExpandableSwitchProps>) => {
  const [checked, setChecked] = useState(false);

  const handleChangeCheckedBox = (event: React.ChangeEvent<HTMLInputElement>) => {
    setChecked(event.target.checked);
  };

  return (
    <ExpandableSwitch
      label="Test label"
      isToggled={checked}
      onChange={handleChangeCheckedBox}
      size={args.size}
      disabled={args.disabled}
      variant={args.variant}
    />
  );
};

export const ExpandableSwitchStory: Story = {
  args: {
    size: 'medium',
    variant: 'green',
    disabled: false,
  },
  render: ({ ...args }) => {
    return <SwitchWithHooks {...args} />;
  },
};
