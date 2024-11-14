import { useState } from 'react';
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
  },
  render: (args) => <InputWithAutocompleteStoryWithHooks {...args} />,
};
