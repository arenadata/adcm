import React from 'react';
import AuditHeader from '@layouts/AuditPageLayout/AuditHeader';
import { Outlet } from 'react-router-dom';

const AuditPageLayout = () => {
  return (
    <div>
      <AuditHeader />
      <Outlet />
    </div>
  );
};

export default AuditPageLayout;
