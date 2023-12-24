import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/hostComponents/hostComponentsTableSlice';
import { Pagination, PaginationData } from '@uikit';

const HostComponentsTableFooter: React.FC = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.hostComponents.totalCount);
  const paginationParams = useStore((s) => s.adcm.hostComponentsTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default HostComponentsTableFooter;
