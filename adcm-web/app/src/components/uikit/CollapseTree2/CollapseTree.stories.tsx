import type { Meta, StoryObj } from '@storybook/react';
import Icon from '@uikit/Icon/Icon';
import CollapseNode from './CollapseNode';
import type { Node } from './CollapseNode.types';
import cn from 'classnames';
import s from './CollapseTree.stories.module.scss';

type Story = StoryObj<typeof CollapseNode>;
export default {
  title: 'uikit/CollapseNode',
  component: CollapseNode,
} as Meta<typeof CollapseNode>;

type SomeObject = {
  title: string;
  isValid: boolean;
};

const renderNodeContent = (node: Node<SomeObject>, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => {
  const handleClick = () => {
    onExpand(!isExpanded);
  };

  const className = cn(s.nodeContent, {
    'is-open': isExpanded,
    // 'is-selected': isSelected,
    'is-failed': !node.data.isValid,
  });

  const hasChildren = Boolean(node.children?.length);

  return (
    <div className={className}>
      {!node.data.isValid && <Icon size={14} name="alert-circle" />}
      <span className={s.nodeContent__title}>{node.data.title}</span>
      {hasChildren && <Icon name="chevron" size={12} className={s.nodeContent__arrow} onClick={handleClick} />}
    </div>
  );
};

const getNodeClassName = (node: Node<SomeObject>) =>
  cn(s.collapseNode, {
    [s.collapseNode_failed]: !node.data.isValid,
  });

const CollapseComponentWithHooks = () => {
  const tree: Node<SomeObject> = {
    key: 'root',
    data: {
      title: 'root',
      isValid: false,
    },
    children: [
      {
        key: 'ch1',
        data: {
          title: 'ch1',
          isValid: true,
        },
        children: [
          {
            key: 'ch1-1',
            data: {
              title: 'ch1-1',
              isValid: true,
            },
          },
        ],
      },
      {
        key: 'ch2',
        data: {
          title: 'ch2',
          isValid: false,
        },
      },
    ],
  };

  return (
    <>
      <CollapseNode node={tree} renderNodeContent={renderNodeContent} getNodeClassName={getNodeClassName} />
    </>
  );
};

export const CollapseComponent: Story = {
  render: () => <CollapseComponentWithHooks />,
};
