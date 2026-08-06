import type { Meta, StoryObj } from '@storybook/react';
import { AdcmJobStatus } from '@models/adcm';
import JobsStatusIcon from './JobsStatusIcon';

type Story = StoryObj<typeof JobsStatusIcon>;

const statuses = Object.values(AdcmJobStatus) as AdcmJobStatus[];

export default {
  title: 'common/JobsStatusIcon',
  component: JobsStatusIcon,
} as Meta<typeof JobsStatusIcon>;

export const AllStatuses: Story = {
  render: () => (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: '16px',
      }}
    >
      {statuses.map((status) => (
        <div
          key={status}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            padding: '12px 16px',
            border: '1px solid var(--color-stroke-light)',
            borderRadius: '8px',
          }}
        >
          <JobsStatusIcon status={status} size={32} />
          <span>{status}</span>
        </div>
      ))}
    </div>
  ),
};
