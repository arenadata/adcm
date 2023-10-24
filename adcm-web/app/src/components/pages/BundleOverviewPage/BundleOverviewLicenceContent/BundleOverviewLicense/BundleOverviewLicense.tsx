import React from 'react';
import s from './BundleOverviewLicense.module.scss';

interface BundleOverviewLicense {
  licenseText?: string;
}

const BundleOverviewLicense = ({ licenseText }: BundleOverviewLicense) => {
  return (
    <div className={s.bundleOverviewLicense}>
      <pre>{licenseText}</pre>
    </div>
  );
};

export default BundleOverviewLicense;
