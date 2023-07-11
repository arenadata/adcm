/* eslint-disable react-hooks/rules-of-hooks */
import DatePicker from '@uikit/DatePicker/DatePicker';
import { Meta, StoryObj } from '@storybook/react';
import { useEffect, useState } from 'react';

type Story = StoryObj<typeof DatePicker>;

export default {
  title: 'uikit/DatePicker',
  component: DatePicker,
  argTypes: {
    placeholder: {
      defaultValue: 'Select date...',
      description: 'Placeholder',
      control: { type: 'text' },
    },
    value: {
      defaultValue: new Date(),
      description: 'Value',
      control: { type: 'date' },
    },
  },
} as Meta<typeof DatePicker>;

export const DatePickerStory: Story = {
  args: {
    disabled: false,
    value: new Date(),
  },
  render: ({ value, onSubmit, ...args }) => {
    const [date, setDate] = useState<Date | undefined>(value);

    useEffect(() => {
      setDate(value);
    }, [value]);

    const handleSubmit = (d: Date | undefined) => {
      setDate(d);
      onSubmit && onSubmit(d);
    };

    return (
      <div style={{ width: 300, display: 'flex', alignItems: 'center' }}>
        Start time: <DatePicker {...args} onSubmit={handleSubmit} value={date} />
      </div>
    );
  },
};
