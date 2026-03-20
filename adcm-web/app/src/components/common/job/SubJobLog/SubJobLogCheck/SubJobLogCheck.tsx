import type React from 'react';
import { useCallback, useMemo, useRef } from 'react';
import cn from 'classnames';
import { type AdcmSubJobLogItemCheck, AdcmJobStatus } from '@models/adcm';
import CollapseNode from '@uikit/CollapseTree2/CollapseNode';
import type { SubJobLogNode } from './SubJobLogCheck.types';
import SubJobLogCheckNode from './SubJobLogCheckNode/SubJobLogCheckNode';
import s from './SubJobLogCheck.module.scss';
import { useResizeObserver } from '@hooks';
import { calculateAndSetChildrenBorderHeight, checkItemToNode, getRootNodeStatus } from './SubJobLog.utils';

const handleRenderNodeContent = (logNode: SubJobLogNode, isExpanded: boolean, onExpand: (isOpen: boolean) => void) => (
  <SubJobLogCheckNode logNode={logNode} isExpanded={isExpanded} onExpand={onExpand} />
);

const handleGetNodeClassName = ({ data }: SubJobLogNode) =>
  cn(s.subJobLogCheck__collapseNode, {
    [s.subJobLogCheck__collapseNode_success]: data.status === AdcmJobStatus.Success,
    [s.subJobLogCheck__collapseNode_info]: data.status === AdcmJobStatus.Info,
    [s.subJobLogCheck__collapseNode_warning]: data.status === AdcmJobStatus.Warning,
    [s.subJobLogCheck__collapseNode_failed]: data.status === AdcmJobStatus.Failed,
    [s.subJobLogCheck__collapseNode_running]: data.status === AdcmJobStatus.Running,
  });

interface SubJobLogCheckProps {
  subJobStatus: string;
  log: AdcmSubJobLogItemCheck;
}
const SubJobLogCheck: React.FC<SubJobLogCheckProps> = ({ subJobStatus, log }) => {
  const node = useMemo<SubJobLogNode>(() => {
    const isRootValid = log.content.length !== 0;
    const status = getRootNodeStatus(log.content, subJobStatus);

    return {
      data: {
        subJobStatus,
        status,
        title: 'Log [check]',
        type: 'group',
        message: '',
        result: isRootValid,
      },
      key: 'root',
      index: 0,
      children: log.content.map((logContentItem, index) => checkItemToNode(logContentItem, index)),
    };
  }, [subJobStatus, log]);

  const ref = useRef<HTMLDivElement | null>(null);

  const calculateHeight = useCallback(() => {
    if (!ref.current) return;

    const mainNodeEl = ref.current.querySelector('.collapseNode');
    calculateAndSetChildrenBorderHeight(mainNodeEl);
  }, [ref]);

  useResizeObserver(ref, calculateHeight);

  return (
    <div className={s.subJobLogCheck} ref={ref}>
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
