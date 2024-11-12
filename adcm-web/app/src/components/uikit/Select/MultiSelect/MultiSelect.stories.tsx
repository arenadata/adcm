import React, { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';

type Story = StoryObj<typeof MultiSelect>;

export default {
  title: 'uikit/Select',
  argTypes: {
    isSearchable: {
      control: { type: 'boolean' },
    },
    checkAllLabel: {
      control: { type: 'text' },
    },
    maxHeight: {
      control: { type: 'number' },
    },
  },
  component: MultiSelect,
} as Meta<typeof MultiSelect>;

const options = [
  {
    value: 123,
    label: 'A 123',
  },
  {
    value: 234,
    label: 'A 234',
  },
  {
    value: 345,
    label: 'A 345',
  },
  {
    value: 456,
    label: 'A 456',
  },
  {
    value: 567,
    label: 'A 567',
  },
  {
    value: 678,
    label: 'A 678',
  },
  {
    value: 789,
    label: 'A 789',
  },
];

type MultiSelectExampleProps = {
  isSearchable?: boolean;
  checkAllLabel?: string;
  searchPlaceholder?: string;
  maxHeight?: number;
};

const MultiSelectExample: React.FC<MultiSelectExampleProps> = ({
  isSearchable,
  checkAllLabel,
  searchPlaceholder,
  maxHeight,
}) => {
  const [value, setValue] = useState<number[]>([]);

  return (
    <div style={{ padding: 30 }}>
      <MultiSelect
        value={value}
        onChange={setValue}
        options={options}
        isSearchable={isSearchable}
        checkAllLabel={checkAllLabel}
        searchPlaceholder={searchPlaceholder}
        maxHeight={maxHeight}
        style={{ maxWidth: 300 }}
      />
    </div>
  );
};

export const MultiSelectEasy: Story = {
  args: {
    isSearchable: false,
    checkAllLabel: undefined,
    searchPlaceholder: 'Search hosts',
  },
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  render: ({ isSearchable, checkAllLabel, searchPlaceholder, maxHeight }) => {
    return (
      <MultiSelectExample
        isSearchable={isSearchable}
        checkAllLabel={checkAllLabel}
        searchPlaceholder={searchPlaceholder}
        maxHeight={maxHeight}
      />
    );
  },
};
