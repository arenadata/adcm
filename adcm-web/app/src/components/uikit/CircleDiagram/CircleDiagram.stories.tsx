import CircleDiagram, { CircleDiagramProps } from './CircleDiagram';
import { Meta, StoryObj } from '@storybook/react';
import s from './CircleDiagram.stories.module.scss';
import { useState } from 'react';

type Story = StoryObj<typeof CircleDiagram>;
export default {
  title: 'uikit/CircleDiagram',
  component: CircleDiagram,
  argTypes: {
    totalCount: {
      description: 'Total count',
    },
    currentCount: {
      description: 'Current count',
    },
    className: {
      description: 'Class must includes "color" param',
    },
  },
} as Meta<typeof CircleDiagram>;

export const CircleDiagramExample: Story = {
  args: {
    totalCount: 10,
    currentCount: 2,
    className: 'green',
  },
  render: ({ totalCount, currentCount, className }) => {
    return <DiagramExample totalCount={totalCount} currentCount={currentCount} className={className} />;
  },
};

const DiagramExample = ({ totalCount, currentCount, className }: CircleDiagramProps) => {
  const [currentColor, setCurrentColor] = useState(className);
  const prepColorClass = currentColor === 'green' ? s.diagramExampleClass_green : s.diagramExampleClass_yellow;

  return (
    <div className={s.diagramExample}>
      <CircleDiagram currentCount={currentCount} totalCount={totalCount} className={prepColorClass} />
      <div
        className={s.diagramExample__radioGroup}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setCurrentColor(e.target.value)}
      >
        <label>
          <input type="radio" value="green" name="color" /> Green color
        </label>
        <label>
          <input type="radio" value="yellow" name="color" /> Yellow color
        </label>
      </div>
    </div>
  );
};
