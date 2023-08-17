import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/jobs/jobsTableSlice';
import { Pagination, PaginationData } from '@uikit';

const JobsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.jobs.totalCount);
  const paginationParams = useStore((s) => s.adcm.jobsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default JobsTableFooter;
