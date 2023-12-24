import React, { useMemo } from 'react';
import cn from 'classnames';
import { AdcmJobLogCheckContentItem, AdcmJobLogItemCheck } from '@models/adcm';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import { JobLogNode } from './JobLogCheck.types';
import JobLogCheckNode from './JobLogCheckNode/JobLogCheckNode';
import s from './JobLogCheck.module.scss';

const handleRenderNodeContent = (logNode: JobLogNode, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => (
  <JobLogCheckNode logNode={logNode} isExpanded={isExpanded} onExpand={onExpand} />
);
const handleGetNodeClassName = (logNode: JobLogNode) =>
  cn(s.jobLogCheck__collapseNode, {
    [s.jobLogCheck__collapseNode_failed]: !logNode.data.result,
  });

const checkItemToNode = ({ content, ...data }: AdcmJobLogCheckContentItem, key: number): JobLogNode => {
  return {
    data,
    key: `${key}`,
    children: content?.map((item, index) => checkItemToNode(item, index)),
  };
};

interface JobLogCheckProps {
  jobStatus: string;
  log: AdcmJobLogItemCheck;
}
const JobLogCheck: React.FC<JobLogCheckProps> = ({ jobStatus, log }) => {
  const node = useMemo<JobLogNode>(() => {
    const isRootValid = log.content.length === 0 || log.content.every((item) => item.result);
    return {
      data: {
        jobStatus,
        title: 'Log [check]',
        type: 'group',
        message: '',
        result: isRootValid,
      },
      key: 'root',
      children: log.content.map((logContentItem, index) => checkItemToNode(logContentItem, index)),
    };
  }, [jobStatus, log]);

  return (
    <div className={s.jobLogCheck}>
      <CollapseNode
        node={node}
        isInitiallyExpanded={true}
        getNodeClassName={handleGetNodeClassName}
        renderNodeContent={handleRenderNodeContent}
      />
    </div>
  );
};
export default JobLogCheck;
