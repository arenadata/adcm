import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/cluster/hosts/host/clusterHostTableSlice';
import { Pagination, PaginationData } from '@uikit';

const HostComponentsTableFooter: React.FC = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.clusterHost.hostComponentsCounters.totalHostComponentsCount);
  const paginationParams = useStore((s) => s.adcm.clusterHostTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default HostComponentsTableFooter;
