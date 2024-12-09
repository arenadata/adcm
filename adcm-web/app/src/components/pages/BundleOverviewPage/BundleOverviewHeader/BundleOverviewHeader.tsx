import type React from 'react';
import s from './BundleOverviewHeader.module.scss';
import { useStore } from '@hooks';
import { orElseGet } from '@utils/checkUtils';
import EntityHeader from '@commonComponents/EntityHeader/EntityHeader';
import BundleDeleteButton from './BundleDeleteButton/BundleDeleteButton';

const BundleOverviewHeader: React.FC = () => {
  const bundle = useStore(({ adcm }) => adcm.bundle.bundle);
  return (
    <div className={s.bundleOverviewHeader}>
      <EntityHeader title={orElseGet(bundle?.displayName)} actions={<BundleDeleteButton />} />
    </div>
  );
};

export default BundleOverviewHeader;
