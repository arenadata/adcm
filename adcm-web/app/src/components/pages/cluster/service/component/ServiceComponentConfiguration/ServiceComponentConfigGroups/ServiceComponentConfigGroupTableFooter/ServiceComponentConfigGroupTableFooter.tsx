import { useDispatch, useStore } from '@hooks';
import { Pagination, PaginationData } from '@uikit';
import { setPaginationParams } from '@store/adcm/cluster/services/serviceComponents/serviceComponent/configGroups/serviceComponentConfigGroupsTableSlice';

const ServiceComponentConfigGroupTableFooter = () => {
  const dispatch = useDispatch();

  const totalCount = useStore(({ adcm }) => adcm.serviceComponentConfigGroups.totalCount);
  const paginationParams = useStore(({ adcm }) => adcm.serviceComponentConfigGroupsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default ServiceComponentConfigGroupTableFooter;
