import type { Meta, StoryObj } from '@storybook/react';
import Statusable from '@uikit/Statusable/Statusable';

type Story = StoryObj<typeof Statusable>;
export default {
  title: 'uikit/Statusable',
  component: Statusable,
  argTypes: {
    children: {
      control: { type: 'text' },
    },
  },
} as Meta<typeof Statusable>;

export const StatusableText: Story = {
  args: {
    children: 'Some text',
    size: 'medium',
    status: 'done',
  },
  render: ({ children, ...args }) => {
    return <Statusable {...args}>{children}</Statusable>;
  },
};

export const StatusableLink: Story = {
  args: {
    children: 'Some text',
    size: 'medium',
    status: 'done',
  },
  render: ({ children, ...args }) => {
    return (
      <Statusable {...args}>
        <a className="text-link" href="/some/url" onClick={(e) => e.preventDefault()}>
          {children}
        </a>
      </Statusable>
    );
  },
};
