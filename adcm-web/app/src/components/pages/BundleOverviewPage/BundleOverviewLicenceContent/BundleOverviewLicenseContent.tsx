import React from 'react';
import BundleOverviewAcceptPanel from './BundleOverviewAcceptPanel/BundleOverviewAcceptPanel';
import BundleOverviewLicense from './BundleOverviewLicense/BundleOverviewLicense';
import { useStore } from '@hooks';
import { AdcmLicenseStatus } from '@models/adcm';

const BundleOverviewLicenseContent = () => {
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);
  const isLicenseAccepted = bundle?.mainPrototype.license.status === AdcmLicenseStatus.Accepted;

  return (
    <>
      <BundleOverviewAcceptPanel
        prototypeId={bundle?.mainPrototype.id}
        bundleId={bundle?.id}
        isLicenseAccepted={isLicenseAccepted}
      />
      <BundleOverviewLicense licenseText={bundle?.mainPrototype.license.text} />
    </>
  );
};

export default BundleOverviewLicenseContent;
