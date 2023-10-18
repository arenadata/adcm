import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import React, { useEffect } from 'react';
import { useRequestBundle } from './useRequestBundle';
import BundleOverviewHeader from './BundleOverviewHeader/BundleOverviewHeader';
import BundleOverviewTable from './BundleOverviewTable/BundleOverviewTable';
import BundleOverviewLicenseContent from './BundleOverviewLicenceContent/BundleOverviewLicenseContent';
import { Spinner } from '@uikit';
import s from './BundleOverviewPage.module.scss';

const BundleOverviewPage: React.FC = () => {
  useRequestBundle();
  const dispatch = useDispatch();
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);
  const prototype = useStore(({ adcm }) => adcm.bundle.relatedData.prototype);
  const isBundleLicensePresent = prototype?.license?.text !== null;
  const isLicenseLoading = useStore(({ adcm }) => adcm.bundle.isLicenseLoading);

  useEffect(() => {
    if (bundle) {
      dispatch(setBreadcrumbs([{ href: '/bundles', label: 'Bundles' }, { label: bundle.name }]));
    }
  }, [bundle, dispatch]);

  return (
    <>
      <BundleOverviewHeader />
      <BundleOverviewTable />
      {isLicenseLoading ? (
        <div className={s.spinner}>
          <Spinner />
        </div>
      ) : (
        <>{isBundleLicensePresent && <BundleOverviewLicenseContent />}</>
      )}
    </>
  );
};

export default BundleOverviewPage;
