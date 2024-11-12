import Button from './Button';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof Button>;
export default {
  title: 'uikit/Button',
  component: Button,
  argTypes: {
    disabled: {
      description: 'Disabled',
      control: { type: 'boolean' },
    },
    iconLeft: {
      description: 'Left Icon',
      control: { type: 'text' },
    },
    iconRight: {
      description: 'Right Icon',
      control: { type: 'text' },
    },
  },
} as Meta<typeof Button>;

export const ButtonEasy: Story = {
  args: {
    children: 'Lorem ipsum',
  },
};

export const ButtonWithIcon: Story = {
  args: {
    children: 'Upgrade',
    variant: 'primary',
    hasError: false,
    disabled: false,
    iconLeft: 'g1-imports',
  },
  render: ({ children, ...args }) => {
    return <Button {...args}>{children}</Button>;
  },
};

export const ButtonWithIconExamples: Story = {
  render: () => {
    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px' }}>
        <Button>Lorem ipsum</Button>
        <Button iconLeft="g1-actions">Lorem ipsum</Button>
        <Button variant="secondary" iconLeft="g1-imports">
          Upgrade
        </Button>
        <Button variant="secondary" iconRight="g1-imports">
          Delete
        </Button>
        <Button variant="tertiary" iconLeft="g1-return" />
      </div>
    );
  },
};
