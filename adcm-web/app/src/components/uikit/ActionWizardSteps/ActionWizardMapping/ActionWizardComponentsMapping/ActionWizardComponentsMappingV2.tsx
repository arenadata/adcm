import type { ComponentsMappingProps } from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentsMapping';
import { Link } from 'react-router-dom';
import { type AnchorBarItem, AnchorList } from '@uikit';
import { useMemo } from 'react';
import ServiceV2 from '@pages/cluster/ClusterMapping/ComponentsMapping/Service/ServiceV2';
import AnchorBar from '@uikit/AnchorBar/AnchorBar';
import s from './ActionWizardComponentsMapping.module.scss';
import type { ComponentHostRelations } from '@utils/mapping/mapping.types';

const buildServiceAnchorId = (id: number) => `anchor_${id}`;

export type ActionComponentsMappingV2Props = Omit<
  ComponentsMappingProps,
  'onInstallServices' | 'initiallyMappedHosts'
> & {
  clusterId: number | null;
  onClose: () => void;
  isReadOnly?: boolean;
  relations: ComponentHostRelations;
};

const ActionWizardComponentsMappingV2 = ({
  clusterId,
  servicesMapping,
  onClose,
  isReadOnly = false,
  relations,
  ...restProps
}: ActionComponentsMappingV2Props) => {
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
          <ServiceV2
            key={service.id}
            service={service}
            componentsMapping={componentsMapping}
            hasErrors={hasErrors}
            anchorId={buildServiceAnchorId(service.id)}
            isReadOnly={isReadOnly}
            relations={relations}
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

export default ActionWizardComponentsMappingV2;
