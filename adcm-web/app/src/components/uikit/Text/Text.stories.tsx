import Text from '@uikit/Text/Text';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof Text>;
export default {
  title: 'uikit/Text',
  component: Text,
  argTypes: {
    variant: {
      description: 'Variant',
      defaultValue: 'h1',
      options: ['h1', 'h2', 'h3', 'h4'],
      control: { type: 'radio' },
    },
    className: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof Text>;

export const TextElement: Story = {
  args: {
    variant: 'h1',
  },
  render: (args) => {
    return <Text {...args}>Something text</Text>;
  },
};
