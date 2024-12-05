import s from './BundleOverviewLicense.module.scss';

interface BundleOverviewLicense {
  licenseText?: string | null;
}

const BundleOverviewLicense = ({ licenseText }: BundleOverviewLicense) => {
  return (
    <div className={s.bundleOverviewLicense}>
      <pre>{licenseText}</pre>
    </div>
  );
};

export default BundleOverviewLicense;
