import React from 'react';
import { AdcmDependOnService, AdcmPrototypeShortView } from '@models/adcm';
import { useStore } from '@hooks';
import MarkedList from '@uikit/MarkedList/MarkedList';
import s from './ShowServices.module.scss';
import WarningMessage from '@uikit/WarningMessage/WarningMessage';

const getComponentKey = (item: AdcmPrototypeShortView) => item.id;
const renderComponentItem = (item: AdcmPrototypeShortView) => <div>{item.displayName}</div>;
const getServiceKey = (item: AdcmDependOnService['servicePrototype']) => item.id;
const renderServiceItem = (item: AdcmDependOnService['servicePrototype']) => (
  <>
    <div>{item.displayName}</div>
    <MarkedList list={item.componentPrototypes} renderItem={renderComponentItem} getItemKey={getComponentKey} />
  </>
);

interface ShowServicesProps {
  dependsServices: AdcmDependOnService['servicePrototype'][];
  unacceptedSelectedServices: AdcmDependOnService['servicePrototype'][];
}
const ShowServices: React.FC<ShowServicesProps> = ({ dependsServices, unacceptedSelectedServices }) => {
  const srcComponent = useStore(({ adcm }) => adcm.clusterMapping.requiredServicesDialog.component);
  const hasUnacceptedSelectedServices = unacceptedSelectedServices.length > 0;

  return (
    <div>
      <div className={s.showServices__disclaimer}>
        Selected components require the following objects to be added to the cluster:
      </div>

      <div className={s.showServices__component}>
        <strong>{srcComponent?.displayName}:</strong>
      </div>

      <MarkedList list={dependsServices} getItemKey={getServiceKey} renderItem={renderServiceItem} />

      {hasUnacceptedSelectedServices && (
        <WarningMessage
          className={s.showServices__warning}
          children="Services you selected require you to accept Terms of Agreement"
        />
      )}
    </div>
  );
};

export default ShowServices;
