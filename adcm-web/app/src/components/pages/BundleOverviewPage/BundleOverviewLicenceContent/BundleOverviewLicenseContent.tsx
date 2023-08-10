import React from 'react';
import BundleOverviewAcceptPanel from './BundleOverviewAcceptPanel/BundleOverviewAcceptPanel';
import BundleOverviewLicense from './BundleOverviewLicense/BundleOverviewLicense';
import { useStore } from '@hooks';

const BundleOverviewLicenseContent = () => {
  const prototype = useStore(({ adcm }) => adcm.bundle.relatedData.prototype);
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);
  const isLicenseAccepted = prototype?.license.status === 'accepted';

  return (
    <>
      <BundleOverviewAcceptPanel
        prototypeId={prototype?.id}
        bundleId={bundle?.id}
        isLicenseAccepted={isLicenseAccepted}
      />
      <BundleOverviewLicense licenseText={prototype?.license.text} />
    </>
  );
};

export default BundleOverviewLicenseContent;
