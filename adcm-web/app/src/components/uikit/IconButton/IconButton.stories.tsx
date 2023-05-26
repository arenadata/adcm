import IconButtonComponent from './IconButton';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof IconButtonComponent>;
export default {
  title: 'uikit/Icon',
  component: IconButtonComponent,
  argTypes: {
    disabled: {
      description: 'Disabled',
      control: { type: 'boolean' },
    },
    icon: {
      description: 'Disabled',
      control: { type: 'text' },
    },
  },
} as Meta<typeof IconButtonComponent>;

export const IconButton: Story = {
  args: {
    icon: 'g1-imports',
    size: 32,
    disabled: false,
  },
  render: (args) => {
    return (
      <div style={{ display: 'flex', gap: '20px' }}>
        <IconButtonComponent {...args} />
        <IconButtonComponent {...args} icon="g1-delete" />
        <IconButtonComponent {...args} icon="g1-add" />
        <IconButtonComponent {...args} icon="g1-power-on" />
      </div>
    );
  },
};
