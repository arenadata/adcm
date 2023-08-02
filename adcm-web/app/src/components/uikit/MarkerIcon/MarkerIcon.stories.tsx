import MarkerIcon from './MarkerIcon';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof MarkerIcon>;
export default {
  title: 'uikit/Icon',
  component: MarkerIcon,
} as Meta<typeof MarkerIcon>;

export const MarkerIconsExamples: Story = {
  render: () => {
    return (
      <div style={{ display: 'flex', gap: '40px' }}>
        <MarkerIcon type="alert" />
        <MarkerIcon type="warning" />
        <MarkerIcon type="check" />
        <MarkerIcon type="info" />
      </div>
    );
  },
};
