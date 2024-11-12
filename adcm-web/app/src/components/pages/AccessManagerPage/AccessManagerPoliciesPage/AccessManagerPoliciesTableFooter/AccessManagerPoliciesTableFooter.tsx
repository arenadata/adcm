import React from 'react';
import { useDispatch, useStore } from '@hooks';
import { setPaginationParams } from '@store/adcm/policies/policiesTableSlice';
import type { PaginationData } from '@uikit';
import { Pagination } from '@uikit';

const AccessManagerPoliciesTableFooter: React.FC = () => {
  const dispatch = useDispatch();

  const totalCount = useStore((s) => s.adcm.policies.totalCount);
  const paginationParams = useStore((s) => s.adcm.policiesTable.paginationParams);

  const handlePaginationChange = (params: PaginationData) => {
    dispatch(setPaginationParams(params));
  };

  return <Pagination totalItems={totalCount} pageData={paginationParams} onChangeData={handlePaginationChange} />;
};

export default AccessManagerPoliciesTableFooter;
