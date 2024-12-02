import React, { useMemo } from 'react';
import cn from 'classnames';
import type { AdcmSubJobLogCheckContentItem, AdcmSubJobLogItemCheck } from '@models/adcm';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import type { SubJobLogNode } from './SubJobLogCheck.types';
import SubJobLogCheckNode from './SubJobLogCheckNode/SubJobLogCheckNode';
import s from './SubJobLogCheck.module.scss';

const handleRenderNodeContent = (logNode: SubJobLogNode, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => (
  <SubJobLogCheckNode logNode={logNode} isExpanded={isExpanded} onExpand={onExpand} />
);
const handleGetNodeClassName = (logNode: SubJobLogNode) =>
  cn(s.subJobLogCheck__collapseNode, {
    [s.subJobLogCheck__collapseNode_failed]: !logNode.data.result,
  });

const checkItemToNode = ({ content, ...data }: AdcmSubJobLogCheckContentItem, key: number): SubJobLogNode => {
  return {
    data,
    key: `${key}`,
    children: content?.map((item, index) => checkItemToNode(item, index)),
  };
};

interface SubJobLogCheckProps {
  subJobStatus: string;
  log: AdcmSubJobLogItemCheck;
}
const SubJobLogCheck: React.FC<SubJobLogCheckProps> = ({ subJobStatus, log }) => {
  const node = useMemo<SubJobLogNode>(() => {
    const isRootValid = log.content.length === 0 || log.content.every((item) => item.result);
    return {
      data: {
        subJobStatus,
        title: 'Log [check]',
        type: 'group',
        message: '',
        result: isRootValid,
      },
      key: 'root',
      children: log.content.map((logContentItem, index) => checkItemToNode(logContentItem, index)),
    };
  }, [subJobStatus, log]);

  return (
    <div className={s.subJobLogCheck}>
      <CollapseNode
        node={node}
        isInitiallyExpanded={true}
        getNodeClassName={handleGetNodeClassName}
        renderNodeContent={handleRenderNodeContent}
      />
    </div>
  );
};
export default SubJobLogCheck;
