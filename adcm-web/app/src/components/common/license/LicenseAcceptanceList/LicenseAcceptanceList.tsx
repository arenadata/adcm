import type React from 'react';
import { Fragment, useMemo, useState } from 'react';
import TabButton from '@uikit/Tabs/TabButton';
import type { AdcmPrototype } from '@models/adcm';
import { AdcmLicenseStatus } from '@models/adcm';
import { Panel, TabsBlock } from '@uikit';
import { orElseGet } from '@utils/checkUtils';
import LicenseText from '@commonComponents/license/LicenseText/LicenseText';
import LicenseAcceptancePanel from '@commonComponents/license/LicenseAcceptancePanel/LicenseAcceptancePanel';
import s from './LicenseAcceptanceList.module.scss';
import cn from 'classnames';

type LicenseAcceptanceItem = Pick<AdcmPrototype, 'id' | 'displayName' | 'license'>;

interface LicenseAcceptanceListProps {
  items: LicenseAcceptanceItem[];
  className?: string;
  onAccept: (prototypeId: number) => void;
}

const LicenseAcceptanceList: React.FC<LicenseAcceptanceListProps> = ({ className, items, onAccept }) => {
  const [currentItemId, setCurrentItemId] = useState<number | null>(items[0]?.id ?? null);

  const currentLicenseItem = useMemo(() => items.find((item) => item.id === currentItemId), [items, currentItemId]);

  const handleChangeStep = (event: React.MouseEvent<HTMLButtonElement>) => {
    const itemId = orElseGet(Number(event.currentTarget.dataset.itemId), undefined, null);
    setCurrentItemId(itemId);
  };

  const getAcceptingHandler = (prototype: LicenseAcceptanceItem) => () => {
    onAccept(prototype.id);
    // switch to next service
    if (currentLicenseItem) {
      const currentIndex = items.indexOf(currentLicenseItem);
      const nextItem = items[currentIndex + 1];
      if (nextItem) {
        setCurrentItemId(nextItem.id);
      }
    }
  };

  return (
    <div className={className}>
      <TabsBlock variant="secondary" className={s.licenseAcceptanceList__tabs}>
        {items.map((item) => (
          <TabButton
            isActive={currentItemId === item.id}
            data-item-id={item.id}
            onClick={handleChangeStep}
            key={item.id}
            className={cn({
              [s.licenseAcceptanceList__tab_licenseAccepted]: item.license.status === AdcmLicenseStatus.Accepted,
            })}
          >
            {item.displayName}
          </TabButton>
        ))}
      </TabsBlock>

      {currentLicenseItem && (
        <Fragment key={currentLicenseItem.id}>
          <LicenseAcceptancePanel
            licenseStatus={currentLicenseItem.license.status}
            onAccept={getAcceptingHandler(currentLicenseItem)}
          />
          <Panel variant="secondary">
            <LicenseText className={cn(s.licenseAcceptanceList__text, 'scroll')}>
              {currentLicenseItem.license.text}
            </LicenseText>
          </Panel>
        </Fragment>
      )}
    </div>
  );
};
export default LicenseAcceptanceList;
