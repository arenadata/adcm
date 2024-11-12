import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/audit/auditLogins/auditLoginsTableSlice';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';

const AuditLoginsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.auditLogins.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.auditLoginsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default AuditLoginsTableFooter;
