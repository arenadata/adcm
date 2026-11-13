import { useCallback, useState } from 'react';
import { useStore } from '@hooks';
import { JobExecutionGraph, useExecutionGraphNodeAction } from '@commonComponents/JobExecutionGraph';
import s from './JobExecutionGraphPanel.module.scss';

const JobExecutionGraphPanel = () => {
  const executionPlan = useStore(({ adcm }) => adcm.job.executionPlan);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const handleNodeAction = useExecutionGraphNodeAction();

  const handleNodeClick = useCallback(({ nodeId }: { nodeId: string }) => {
    setSelectedNodeId(nodeId);
  }, []);

  if (!executionPlan) {
    return (
      <div className={s.fallback} data-test="job-execution-graph-fallback">
        Execution plan is unavailable. Switch to Table view to see subjobs.
      </div>
    );
  }

  return (
    <div className={s.panel} data-test="job-execution-graph-panel">
      <JobExecutionGraph
        plan={executionPlan}
        selectedNodeId={selectedNodeId}
        onNodeClick={handleNodeClick}
        onNodeAction={handleNodeAction}
      />
    </div>
  );
};

export default JobExecutionGraphPanel;
