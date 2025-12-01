import { FlexGroup } from '@uikit';
import type { AdcmUpgradeShort } from '@models/adcm';
import s from './BundleVersionTooltipContent.module.scss';

export interface BundleVersionTooltipContentRowProps {
  label: string;
  value: string;
}

const BundleVersionTooltipContentRow = ({ label, value }: BundleVersionTooltipContentRowProps) => (
  <FlexGroup gap={6} justifyContent="flex-start">
    <span className={s.bundleVersionTooltipContent__label}>{label}:</span>
    <span className={s.bundleVersionTooltipContent__value}>{value}</span>
  </FlexGroup>
);

export interface BundleVersionTooltipContentProps {
  version: AdcmUpgradeShort;
}

const BundleVersionTooltipContent = (props: BundleVersionTooltipContentProps) => {
  const { version } = props;

  return (
    <div className={s.bundleVersionTooltipContent}>
      <BundleVersionTooltipContentRow label="Product" value={version.bundle.displayName} />
      <BundleVersionTooltipContentRow label="Version" value={version.bundle.version} />
      <BundleVersionTooltipContentRow label="Edition" value={version.bundle.edition} />
    </div>
  );
};

export default BundleVersionTooltipContent;
