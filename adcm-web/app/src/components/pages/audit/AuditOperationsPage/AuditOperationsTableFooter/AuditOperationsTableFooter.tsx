import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/audit/auditOperations/auditOperationsTableSlice';
import { Pagination, PaginationData } from '@uikit';

const AuditOperationsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.auditOperations.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.auditOperationsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default AuditOperationsTableFooter;
