import VirtualList from './VirtualList';
import type { Meta, StoryObj } from '@storybook/react';
import s from './VirtualList.stories.module.scss';

type DemoItem = {
  id: number;
  label: string;
};

const demoItems: DemoItem[] = Array.from({ length: 100 }, (_, index) => ({
  id: index,
  label: `Item ${index + 1}`,
}));

type Story = StoryObj<typeof VirtualList>;

export default {
  title: 'uikit/VirtualList',
  component: VirtualList,
  argTypes: {
    estimateSize: {
      control: { type: 'number' },
    },
    gap: {
      control: { type: 'number' },
    },
    measureItems: {
      control: { type: 'boolean' },
    },
  },
} as Meta<typeof VirtualList>;

export const Default: Story = {
  render: () => (
    <VirtualList
      items={demoItems}
      className={s.virtualListStory}
      getItemKey={(item) => item.id}
      estimateSize={28}
      gap={6}
      measureItems={false}
      renderItem={(item) => <span className={s.virtualListStory__item}>{item.label}</span>}
    />
  ),
};

export const Empty: Story = {
  render: () => (
    <VirtualList
      items={[]}
      className={s.virtualListStory}
      emptyContent={<span className={s.virtualListStory__empty}>No data</span>}
      renderItem={() => null}
    />
  ),
};
