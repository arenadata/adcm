import type { Meta, StoryObj } from '@storybook/react';
import ShowMore from './ShowMore';

type Story = StoryObj<typeof ShowMore>;

const longText = (
  <>
    <p>
      The main goal of ADS bundle is an easy and fast installation and managing of Arenadata Streaming with Arenadata
      Cluster Manager.
    </p>
    <p>
      ADS bundle consists of services: ZooKeeper, Kafka Broker, Schema-Registry, Kafka REST Proxy, ksqlDB, Kafka
      Connect, NiFi, NiFi Registry, and Monitoring. Each service can be configured independently and mapped to selected
      hosts.
    </p>
    <p>
      Additional notes describe upgrade paths, maintenance mode behavior, and recommended topology for production
      clusters.
    </p>
  </>
);

export default {
  title: 'uikit/ShowMore',
  component: ShowMore,
  argTypes: {
    maxLines: {
      control: { type: 'number', min: 1, max: 10 },
    },
    showMoreLabel: {
      control: { type: 'text' },
    },
    showLessLabel: {
      control: { type: 'text' },
    },
  },
} as Meta<typeof ShowMore>;

export const Default: Story = {
  args: {
    maxLines: 3,
  },
  render: (args) => (
    <div style={{ maxWidth: 480 }}>
      <ShowMore {...args}>{longText}</ShowMore>
    </div>
  ),
};

export const ShortContent: Story = {
  render: () => (
    <div style={{ maxWidth: 480 }}>
      <ShowMore maxLines={3}>
        <p>Short bundle description without overflow. Toggle is hidden.</p>
      </ShowMore>
    </div>
  ),
};

export const TwoLines: Story = {
  args: {
    maxLines: 2,
  },
  render: (args) => (
    <div style={{ maxWidth: 480 }}>
      <ShowMore {...args}>{longText}</ShowMore>
    </div>
  ),
};
