import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/users/usersTableSlice';
import { Pagination, PaginationData } from '@uikit';

const AccessManagerUsersTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.users.totalCount);
  const paginationParams = useStore((s) => s.adcm.usersTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default AccessManagerUsersTableFooter;
