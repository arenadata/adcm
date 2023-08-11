import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/groups/groupsTableSlice';
import { Pagination, PaginationData } from '@uikit';

const AccessManagerGroupsTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.groups.totalCount);
  const paginationParams = useStore((s) => s.adcm.groupsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default AccessManagerGroupsTableFooter;
