import React from 'react';
import Text from '@uikit/Text/Text';
import Breadcrumbs from '@layouts/partials/Breadcrumbs/Breadcrumbs';
import { usePageRouteInfo } from '@hooks';

import s from './PageHeader.module.scss';

const PageHeader: React.FC = () => {
  const { pageTitle, breadcrumbs } = usePageRouteInfo();
  return (
    <>
      <div className={s.pageHeader}>
        <Text variant="h1" className="green-text">
          {pageTitle}
        </Text>
        <Breadcrumbs list={breadcrumbs} />
      </div>
    </>
  );
};

export default PageHeader;
