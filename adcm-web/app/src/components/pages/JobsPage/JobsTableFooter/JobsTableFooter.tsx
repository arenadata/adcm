import FrequencySelect from '@commonComponents/Table/FrequencySelect/FrequencySelect';
import { useDispatch, useStore } from '@hooks';
import { setPaginationParams, setRequestFrequency } from '@store/adcm/jobs/jobsTableSlice';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';

const JobsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.jobs.totalCount);
  const paginationParams = useStore((s) => s.adcm.jobsTable.paginationParams);
  const requestFrequency = useStore((s) => s.adcm.jobsTable.requestFrequency);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  const handleFrequencyChange = (frequency: number) => {
    dispatch(setRequestFrequency(frequency));
  };

  return (
    <Pagination
      totalItems={totalCount}
      pageData={paginationParams}
      onChangeData={handlePaginationChange}
      frequencyComponent={<FrequencySelect value={requestFrequency} onChange={handleFrequencyChange} />}
    />
  );
};

export default JobsTableFooter;
