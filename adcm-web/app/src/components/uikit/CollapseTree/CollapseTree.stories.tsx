import { Meta, StoryObj } from '@storybook/react';
import CollapseTree from './CollapseTree';
import NodeContent, { Node } from './NodeContent/NodeContent';
import cn from 'classnames';
import s from './NodeContent/NodeContent.module.scss';

type Story = StoryObj<typeof CollapseTree>;
export default {
  title: 'uikit/CollapseTree',
  component: CollapseTree,
} as Meta<typeof CollapseTree>;

const renderItem = (node: Node, isExpanded: boolean) => (
  <NodeContent
    node={node}
    isExpanded={isExpanded}
    isSelected={false}
    onClick={(node: Node) => {
      console.info(node.title);
    }}
  />
);

const getNodeClassName = (node: Node) =>
  cn(s.collapseTreeNode, {
    [s.collapseTreeNode_failed]: !node.isValid,
  });

const CollapseComponentWithHooks = () => {
  const model: Node = {
    title: 'root',
    isValid: false,
    children: [
      {
        title: 'ch1',
        isValid: true,
        children: [
          {
            title: 'ch1-1',
            isValid: true,
          },
        ],
      },
      {
        title: 'ch2',
        isValid: false,
      },
    ],
  };

  return (
    <>
      <CollapseTree
        model={model}
        childFieldName="children"
        renderNode={renderItem}
        uniqueFieldName="title"
        getNodeClassName={getNodeClassName}
      />
    </>
  );
};

export const CollapseComponent: Story = {
  render: () => <CollapseComponentWithHooks />,
};
