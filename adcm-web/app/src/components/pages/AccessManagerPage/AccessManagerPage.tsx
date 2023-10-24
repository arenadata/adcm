import React from 'react';
import AccessManagerHeader from './AccessManagerHeader';
import { Outlet } from 'react-router-dom';

const AccessManagerPage: React.FC = () => {
  return (
    <div>
      <AccessManagerHeader />
      <Outlet />
    </div>
  );
};

export default AccessManagerPage;
