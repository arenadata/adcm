import type { ComponentsMappingProps } from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentsMapping';
import { Link } from 'react-router-dom';
import { type AnchorBarItem, AnchorList } from '@uikit';
import { useMemo } from 'react';
import ActionWizardMappingService from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMappingService/ActionWizardMappingService';
import AnchorBar from '@uikit/AnchorBar/AnchorBar';
import s from './ActionWizardComponentsMapping.module.scss';
import type { AdcmActionProcessMappingStepRules } from '@models/adcm/wizard';
import type { SortDirection } from '@models/table.ts';
import { sortExtendedActionWizardServicesMapping } from '@uikit/ActionWizardSteps/ActionWizardMapping/ActionWizardMapping.utils.ts';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

export interface ActionComponentsMappingProps extends Omit<ComponentsMappingProps, 'onInstallServices'> {
  rules: AdcmActionProcessMappingStepRules[];
  initiallyMappedHosts: Record<number, Set<number>>;
  clusterId: number | null;
  onClose: () => void;
  isReadOnly?: boolean;
  sortDirection: SortDirection;
}

const ActionWizardComponentsMapping = ({
  clusterId,
  servicesMapping,
  rules,
  initiallyMappedHosts,
  onClose,
  isReadOnly = false,
  sortDirection,
  ...restProps
}: ActionComponentsMappingProps) => {
  const sortingServiceMapping = useMemo(() => {
    return sortExtendedActionWizardServicesMapping(servicesMapping, rules, sortDirection);
  }, [servicesMapping, rules, sortDirection]);

  const anchorItems: AnchorBarItem[] = useMemo(
    () =>
      sortingServiceMapping.map((m) => ({
        label: m.service.displayName,
        id: buildServiceAnchorId(m.service.id),
      })),
    [sortingServiceMapping],
  );

  return (
    <div className={s.componentsMapping}>
      <div data-test="mapping-container">
        {sortingServiceMapping.map(({ service, componentsMapping, hasErrors }) => (
          <ActionWizardMappingService
            key={service.id}
            service={service}
            componentsMapping={componentsMapping}
            hasErrors={hasErrors}
            anchorId={buildServiceAnchorId(service.id)}
            initiallyMappedHosts={initiallyMappedHosts}
            isReadOnly={isReadOnly}
            {...restProps}
          />
        ))}
        {sortingServiceMapping.length === 0 && (
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
