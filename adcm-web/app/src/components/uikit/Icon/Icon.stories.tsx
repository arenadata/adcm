import Icon from './Icon';
import type { Meta, StoryObj } from '@storybook/react';
import s from './IconStory.module.scss';
import { allowIconsNames } from './sprite';

type Story = StoryObj<typeof Icon>;
export default {
  title: 'uikit/Icon',
  component: Icon,
  argTypes: {
    name: {
      type: 'string',
      name: 'name',
      table: {
        disable: true,
      },
    },
    size: {
      description: 'Size',
      defaultValue: 32,
      control: { type: 'number' },
    },
  },
} as Meta<typeof Icon>;

const copyToClipboard = (text: string) => {
  navigator?.clipboard?.writeText(text);
};

export const IconsList: Story = {
  render: (args) => (
    <div className={s.storyIconsWrap}>
      {allowIconsNames.map((name) => (
        <div className={s.storyIconsWrap__item} onClick={() => copyToClipboard(name)} key={name}>
          <Icon {...args} name={name} />
          <div>{name}</div>
        </div>
      ))}
    </div>
  ),
};

IconsList.args = {
  size: 32,
};
