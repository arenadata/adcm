import type { ComponentsMappingProps } from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentsMapping';
import { Link } from 'react-router-dom';
import { type AnchorBarItem, AnchorList } from '@uikit';
import { useMemo } from 'react';
import ActionWizardMappingService from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMappingService/ActionWizardMappingService';
import AnchorBar from '@uikit/AnchorBar/AnchorBar';
import s from './ActionWizardComponentsMapping.module.scss';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

export interface ActionComponentsMappingProps extends Omit<ComponentsMappingProps, 'onInstallServices'> {
  rules: AdcmActionProcessMappingStepRules[];
  initiallyMappedHosts: Record<number, Set<number>>;
  clusterId: number | null;
  onClose: () => void;
  isReadOnly?: boolean;
}

const ActionWizardComponentsMapping = ({
  clusterId,
  servicesMapping,
  rules,
  initiallyMappedHosts,
  onClose,
  isReadOnly = false,
  ...restProps
}: ActionComponentsMappingProps) => {
  const anchorItems: AnchorBarItem[] = useMemo(
    () =>
      servicesMapping.map((m) => ({
        label: m.service.displayName,
        id: buildServiceAnchorId(m.service.id),
      })),
    [servicesMapping],
  );

  return (
    <div className={s.componentsMapping}>
      <div data-test="mapping-container">
        {servicesMapping.map(({ service, componentsMapping, hasErrors }) => (
          <ActionWizardMappingService
            key={service.id}
            service={service}
            componentsMapping={componentsMapping}
            hasErrors={hasErrors}
            anchorId={buildServiceAnchorId(service.id)}
            rules={rules}
            initiallyMappedHosts={initiallyMappedHosts}
            isReadOnly={isReadOnly}
            {...restProps}
          />
        ))}
        {servicesMapping.length === 0 && (
          <div>
            Add services on the{' '}
            <Link className="text-link" to={`/clusters/${clusterId}/services`} onClick={onClose}>
              services page
            </Link>
          </div>
        )}
      </div>
      <AnchorBar>
        <AnchorList items={anchorItems} />
      </AnchorBar>
    </div>
  );
};

export default ActionWizardComponentsMapping;
