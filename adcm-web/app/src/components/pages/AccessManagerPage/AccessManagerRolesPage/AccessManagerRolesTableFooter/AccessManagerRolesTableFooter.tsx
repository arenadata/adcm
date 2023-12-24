import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/roles/rolesTableSlice';
import { Pagination, PaginationData } from '@uikit';

const AccessManagerRolesTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.roles.totalCount);
  const paginationParams = useStore((s) => s.adcm.rolesTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default AccessManagerRolesTableFooter;
