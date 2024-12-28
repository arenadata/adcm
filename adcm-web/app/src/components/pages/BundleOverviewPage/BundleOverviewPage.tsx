import { useDispatch, useStore } from '@hooks';
import { setBreadcrumbs } from '@store/adcm/breadcrumbs/breadcrumbsSlice';
import type React from 'react';
import { useEffect } from 'react';
import { useRequestBundle } from './useRequestBundle';
import BundleOverviewHeader from './BundleOverviewHeader/BundleOverviewHeader';
import BundleOverviewTable from './BundleOverviewTable/BundleOverviewTable';
import BundleOverviewLicenseContent from './BundleOverviewLicenceContent/BundleOverviewLicenseContent';
import { Spinner } from '@uikit';
import s from './BundleOverviewPage.module.scss';
import { isShowSpinner } from '@uikit/Table/Table.utils';

const BundleOverviewPage: React.FC = () => {
  useRequestBundle();
  const dispatch = useDispatch();
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);
  const isBundleLicensePresent = bundle?.mainPrototype.license?.text !== null;
  const isLicenseLoading = useStore(({ adcm }) => isShowSpinner(adcm.bundle.licenseLoadState));

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
