import type React from 'react';
import WarningMessage from '@uikit/WarningMessage/WarningMessage';
import s from './ServicesDependenciesWarning.module.scss';
import type { AdcmServicePrototype } from '@models/adcm';

interface ServicesDependenciesWarningProps {
  dependenciesList: AdcmServicePrototype[];
  className?: string;
}

const ServicesDependenciesWarning: React.FC<ServicesDependenciesWarningProps> = ({ className, dependenciesList }) => {
  return (
    <WarningMessage className={className}>
      {dependenciesList.map((service) => {
        return (
          <div key={service.id} className={s.servicesDependenciesWarning__row}>
            <strong>{service.displayName}</strong> requires installation of{' '}
            {service.dependOn
              ?.map<React.ReactNode>(({ servicePrototype: { id, displayName } }) => (
                <strong key={id}>{displayName}</strong>
              ))
              .reduce((prev, current) => [prev, ', ', current])}
          </div>
        );
      })}
    </WarningMessage>
  );
};

export default ServicesDependenciesWarning;
