import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import Button from '@uikit/Button/Button';
import Collapse from './Collapse';

type Story = StoryObj<typeof Collapse>;
export default {
  title: 'uikit/Collapse',
  component: Collapse,
} as Meta<typeof Collapse>;

const style = {
  color: '#757b81',
  border: '1px solid #757b81',
  marginTop: '20px',
  padding: '16px',
};

const CollapseComponentWithHooks = () => {
  const [isExpanded, setExpanded] = useState(true);

  return (
    <>
      <Button
        onClick={() => {
          setExpanded((prevExpanded) => !prevExpanded);
        }}
      >
        {isExpanded ? 'Close' : 'Open'}
      </Button>

      <Collapse isExpanded={isExpanded}>
        <div style={style}>
          "Lorem ipsum dolor sit amet, consectetur adipiscing elit, <br />
          sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
          <br />
          Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi <br />
          ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit
          <br />
          in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
          <br />
          Excepteur sint occaecat cupidatat non proident, <br />
          sunt in culpa qui officia deserunt mollit anim id est laborum."
          <br />
          <br />
          <br />
        </div>
      </Collapse>
    </>
  );
};

export const CollapseComponent: Story = {
  render: () => <CollapseComponentWithHooks />,
};
