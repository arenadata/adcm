import { useCallback } from 'react';
import { useDispatch } from '@hooks';
import { openStopDialog, openStopGroupDialog } from '@store/adcm/jobs/subJobsActionsSlice';
import type { JobExecutionGraphNodeActionPayload } from './JobExecutionGraph.context';

export const useExecutionGraphNodeAction = () => {
  const dispatch = useDispatch();

  return useCallback(
    ({ data, action }: JobExecutionGraphNodeActionPayload) => {
      if (data.entityKind === 'job') {
        dispatch(openStopDialog({ id: Number(data.entityKey), mode: action, displayName: data.title }));
        return;
      }

      dispatch(openStopGroupDialog({ name: data.entityKey, displayName: data.title, mode: action }));
    },
    [dispatch],
  );
};
