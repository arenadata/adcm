import React from 'react';
import Text from '@uikit/Text/Text';
import Breadcrumbs from '@layouts/partials/Breadcrumbs/Breadcrumbs';
import { usePageRouteInfo, useStore } from '@hooks';

import s from './PageHeader.module.scss';

const PageHeader: React.FC = () => {
  const { breadcrumbs: breadcrumbsStore } = useStore((s) => s.adcm.breadcrumbs);
  const { pageTitle, breadcrumbs: breadcrumbsRoute } = usePageRouteInfo();

  const breadcrumbs = breadcrumbsStore.length ? breadcrumbsStore : breadcrumbsRoute;

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
