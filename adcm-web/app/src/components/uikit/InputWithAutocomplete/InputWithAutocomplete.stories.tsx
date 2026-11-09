import { useMemo, useState } from 'react';
import type { InputWithAutoCompleteProps } from './InputWithAutocomplete';
import InputWithAutocomplete from './InputWithAutocomplete';
import type { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof InputWithAutocomplete>;
export default {
  title: 'uikit/InputWithAutocomplete',
  component: InputWithAutocomplete,
  argTypes: {
    suggestions: {
      description: 'Suggestions',
    },
    isVirtualized: {
      control: { type: 'boolean' },
    },
    disabled: {
      description: 'Disabled',
      control: { type: 'boolean' },
    },
    startAdornment: {
      table: {
        disable: true,
      },
    },
    endAdornment: {
      table: {
        disable: true,
      },
    },
    variant: {
      table: {
        disable: true,
      },
    },
    placeholder: {
      control: { type: 'text' },
    },
  },
} as Meta<typeof InputWithAutocomplete>;

const InputWithAutocompleteStoryWithHooks = (args: InputWithAutoCompleteProps) => {
  const [value, setValue] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  return <InputWithAutocomplete value={value} {...args} onChange={handleChange} />;
};

export const InputWithAutocompleteStory: Story = {
  args: {
    placeholder: 'Some placeholder',
    suggestions: ['One', 'Two', 'three'],
    isVirtualized: false,
  },
  render: (args) => <InputWithAutocompleteStoryWithHooks {...args} />,
};

const LARGE_SUGGESTIONS_COUNT = 5000;

const VirtualizedInputWithAutocompleteExample = () => {
  const suggestions = useMemo(
    () =>
      Array.from({ length: LARGE_SUGGESTIONS_COUNT }, (_, index) => {
        return `table_${index.toString().padStart(4, '0')}_long_suggestion_name`;
      }),
    [],
  );
  const [value, setValue] = useState('');

  return (
    <div style={{ padding: 30, width: 360 }}>
      <p style={{ marginBottom: 12 }}>
        {LARGE_SUGGESTIONS_COUNT.toLocaleString()} suggestions, <code>isVirtualized</code>
      </p>
      <InputWithAutocomplete
        value={value}
        suggestions={suggestions}
        isVirtualized
        placeholder="Select table"
        onChange={(event) => setValue(event.target.value)}
      />
    </div>
  );
};

export const VirtualizedInputWithAutocomplete: Story = {
  render: () => <VirtualizedInputWithAutocompleteExample />,
};
