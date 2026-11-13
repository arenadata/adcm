import { useCallback, useMemo, useState } from 'react';
import { Button, ExpandableRowComponent, NotificationBlock, Table, TableCell } from '@uikit';
import s from './ActionWizardOperation.module.scss';
import { columns } from './ActionWizardOperation.constants';
import { openStopDialog, type SubJobTerminateMode } from '@store/adcm/jobs/subJobsActionsSlice';
import { useDispatch } from '@hooks';
import JobsStatusCell from '@commonComponents/Table/Cells/JobsStatusCell/JobsStatusCell';
import { JobActionIconButton } from '@commonComponents/job/JobActionIconButton/JobActionIconButton';
import { getJobTerminateActions } from '@commonComponents/job/jobTerminateActions';
import StopJobGroupDialog from '@commonComponents/job/StopJobGroupDialog/StopJobGroupDialog';
import JobViewToggle, { type JobViewMode } from '@commonComponents/JobViewToggle/JobViewToggle';
import {
  JobExecutionGraph,
  shouldShowCeleryWorkersNote,
  useExecutionGraphNodeAction,
} from '@commonComponents/JobExecutionGraph';
import { secondsToDuration } from '@utils/date/timeConvertUtils';
import DateTimeCell from '@commonComponents/Table/Cells/DateTimeCell';
import type { AdcmJob, AdcmSubJob, AdcmSubJobDetails, AdcmSubJobLogItem, AdcmTaskExecutionPlan } from '@models/adcm';
import { Link } from 'react-router-dom';
import { orElseGet } from '@utils/checkUtils';
import ActionWizardOperationLog from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardOperationLog/ActionWizardOperationLog';
import ActionWizardStopSubJobDialog from '@uikit/ActionWizardSteps/ActionWizardOperation/ActionWizardStopSubJobDialog/ActionWizardStopSubJobDialog';

interface ActionWizardOperationProps {
  job: AdcmJob;
  subJobLog: Record<AdcmSubJobDetails['id'], AdcmSubJobLogItem[]>;
  executionPlan?: AdcmTaskExecutionPlan | null;
}

const ActionWizardOperation = ({ job, subJobLog, executionPlan = null }: ActionWizardOperationProps) => {
  const dispatch = useDispatch();
  const [expandableRows, setExpandableRows] = useState<Record<number, boolean>>({});
  const [viewMode, setViewMode] = useState<JobViewMode>('table');
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const handleNodeAction = useExecutionGraphNodeAction();

  const showCeleryWorkersNote = useMemo(
    () =>
      shouldShowCeleryWorkersNote({
        plan: executionPlan,
        executionEnvironment: job.executionEnvironment,
      }),
    [executionPlan, job.executionEnvironment],
  );

  const handleExpandClick = (id: number) => {
    setExpandableRows((prev) => ({
      ...prev,
      [id]: prev[id] === undefined ? true : !prev[id],
    }));
  };

  const handleSubJobAction = useCallback(
    (subJob: AdcmSubJob, mode: SubJobTerminateMode) => {
      dispatch(openStopDialog({ id: subJob.id, mode, displayName: subJob.displayName }));
    },
    [dispatch],
  );

  const handleNodeClick = useCallback(({ nodeId }: { nodeId: string }) => {
    setSelectedNodeId(nodeId);
  }, []);

  return (
    <div className={s.root}>
      <div className={s.viewToggle}>
        <JobViewToggle viewMode={viewMode} onChange={setViewMode} />
      </div>

      {viewMode === 'graph' && showCeleryWorkersNote && (
        <NotificationBlock className={s.graphNote}>
          In Celery Worker mode, tasks can be executed in parallel
        </NotificationBlock>
      )}

      {viewMode === 'table' ? (
        <Table variant="secondary" columns={columns}>
          {job.childJobs.map((subJob: AdcmSubJob) => {
            const { isSkipEnabled, isStopEnabled } = getJobTerminateActions(subJob);

            return (
              <ExpandableRowComponent
                key={subJob.id}
                colSpan={columns.length}
                isExpanded={expandableRows[subJob.id] || false}
                expandedContent={<ActionWizardOperationLog subJob={subJob} subJobLogs={subJobLog[subJob.id]} />}
              >
                <JobsStatusCell status={subJob.status} className={s.subJobRow__subJobName}>
                  <Link to={`/jobs/${job.id}/subjobs/${subJob.id}`} className="text-link">
                    {orElseGet(subJob.displayName || null)}
                  </Link>
                </JobsStatusCell>
                <TableCell>{subJob.status}</TableCell>
                <TableCell>{orElseGet(subJob.duration ?? 0, secondsToDuration)}</TableCell>
                <DateTimeCell value={subJob.startTime ?? undefined} />
                <DateTimeCell value={subJob.endTime ?? undefined} />
                <TableCell hasIconOnly align="center">
                  <div className={s.subJobRow__actions}>
                    <JobActionIconButton
                      icon="g1-graph-skip"
                      label="Skip the subjob"
                      disabled={!isSkipEnabled}
                      onClick={() => handleSubJobAction(subJob, 'skip')}
                      data-test="wizard-subjob-skip"
                    />
                    <JobActionIconButton
                      icon="g1-graph-stop"
                      label="Terminate the subjob"
                      disabled={!isStopEnabled}
                      onClick={() => handleSubJobAction(subJob, 'stop')}
                      data-test="wizard-subjob-stop"
                    />
                  </div>
                </TableCell>
                <TableCell hasIconOnly align="center">
                  <Button variant="secondary" iconLeft="dots" onClick={() => handleExpandClick(subJob.id)} />
                </TableCell>
              </ExpandableRowComponent>
            );
          })}
        </Table>
      ) : executionPlan ? (
        <div className={s.graphPanel} data-test="wizard-job-execution-graph">
          <JobExecutionGraph
            plan={executionPlan}
            selectedNodeId={selectedNodeId}
            onNodeClick={handleNodeClick}
            onNodeAction={handleNodeAction}
          />
        </div>
      ) : (
        <div className={s.graphFallback} data-test="wizard-job-execution-graph-fallback">
          Execution plan is unavailable. Switch to Table view to see subjobs.
        </div>
      )}

      <ActionWizardStopSubJobDialog job={job} />
      <StopJobGroupDialog jobId={job.id} />
    </div>
  );
};

export default ActionWizardOperation;
