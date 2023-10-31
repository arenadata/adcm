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
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', width: 'fit-content', gap: '40px' }}>
        <MarkerIcon variant="square" type="alert" />
        <MarkerIcon variant="square" type="warning" />
        <MarkerIcon variant="square" type="check" />
        <MarkerIcon variant="square" type="info" />
        <MarkerIcon variant="round" type="alert" />
        <MarkerIcon variant="round" type="warning" />
        <MarkerIcon variant="round" type="check" />
        <MarkerIcon variant="round" type="info" />
      </div>
    );
  },
};
