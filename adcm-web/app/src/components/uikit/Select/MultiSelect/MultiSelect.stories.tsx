import type React from 'react';
import { type CSSProperties, useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import MultiSelect from '@uikit/Select/MultiSelect/MultiSelect';
import MultiSelectListItem from './MultiSelectList/MultiSelectListItem/MultiSelectListItem';
import Icon from '@uikit/Icon/Icon';
import type { DefaultSelectListItemProps, SelectOption } from '../Select.types';

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

const defaultOptions = [
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
        options={defaultOptions}
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

const CustomSelectItemRender = (props: DefaultSelectListItemProps<number>) => {
  const { disabled, label, value } = props.option;

  const handleChange = () => {
    props.onSelect?.(value);
  };

  const iconStyle: CSSProperties = {
    color: disabled ? 'gray' : props.isSelected ? 'green' : 'inherit',
  };

  return (
    <MultiSelectListItem {...props}>
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center', cursor: 'pointer' }} onClick={handleChange}>
        <Icon name="eye" style={iconStyle} />
        <span>{label}</span>
      </div>
    </MultiSelectListItem>
  );
};

const optionsWithCustomItemRender: SelectOption<number>[] = defaultOptions.map((option) => ({
  ...option,
  ItemComponent: CustomSelectItemRender,
}));

const MultiSelectWithCustomItemRenderExample: React.FC<MultiSelectExampleProps> = ({ isSearchable }) => {
  const [value, setValue] = useState<number[]>([]);

  return (
    <div style={{ padding: 30, maxWidth: 300 }}>
      <MultiSelect
        value={value}
        onChange={setValue}
        options={optionsWithCustomItemRender}
        isSearchable={isSearchable}
        style={{ maxWidth: 300 }}
      />
    </div>
  );
};

export const MultiSelectWithCustomItemRenderStory: Story = {
  args: {},
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  render: () => {
    return <MultiSelectWithCustomItemRenderExample />;
  },
};
