import CircleDiagram from './CircleDiagram';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof CircleDiagram>;

export default {
  title: 'uikit/CircleDiagram',
  component: CircleDiagram,
  argTypes: {
    up: {
      description: 'Up count',
    },
    down: {
      description: 'Down count',
    },
    size: {
      description: 'Diagram size',
      control: { type: 'radio' },
      options: ['small', 'medium'],
    },
  },
} as Meta<typeof CircleDiagram>;

export const CircleDiagramExample: Story = {
  args: {
    up: 15,
    down: 5,
    size: 'small',
  },
};

export const CircleDiagramEmpty: Story = {
  args: {
    up: 0,
    down: 0,
    size: 'small',
  },
};

export const CircleDiagramMedium: Story = {
  args: {
    up: 10,
    down: 5,
    size: 'medium',
  },
};
