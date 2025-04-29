import type React from 'react';
import { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import { Button, ButtonGroup, SearchInput, SpinnerPanel, ToolbarPanel } from '@uikit';
import { useClusterMapping } from '@pages/cluster/ClusterMapping/useClusterMapping';
import { getMappings } from '@store/adcm/entityDynamicActions/dynamicActionsMappingSlice';
import { LoadState } from '@models/loadState';
import type {
  AdcmDynamicActionDetails,
  AdcmDynamicActionRunConfig,
  AdcmHostShortView,
  AdcmMappingComponent,
} from '@models/adcm';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import ComponentContainer from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainer';
import {
  checkComponentActionsMappingAvailability,
  checkHostActionsMappingAvailability,
  checkHostActionsUnmappingAvailability,
  getComponentMapActions,
  getInitiallyMappedHostsDictionary,
} from './DynamicActionHostMapping.utils';

interface DynamicActionHostMappingProps {
  clusterId: number;
  actionDetails: AdcmDynamicActionDetails;
  configuration?: AdcmDynamicActionRunConfig['configuration'] | null;
  onNext: (changes: Partial<AdcmDynamicActionRunConfig>) => void;
  onCancel: () => void;
}

const DynamicActionHostMapping: React.FC<DynamicActionHostMappingProps> = ({
  clusterId,
  actionDetails,
  onNext,
  onCancel,
}) => {
  const dispatch = useDispatch();

  useEffect(() => {
    if (!Number.isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
    }
  }, [clusterId, dispatch]);

  const { hosts, components, mapping, loadState } = useStore(({ adcm }) => adcm.dynamicActionsMapping);

  const notAddedServicesDictionary = useStore(({ adcm }) => adcm.clusterMapping.relatedData.notAddedServicesDictionary);

  const {
    localMapping,
    servicesMapping,
    mappingFilter,
    handleMappingFilterChange,
    mappingErrors,
    handleMapHostsToComponent,
    handleUnmap,
    handleReset,
  } = useClusterMapping(mapping, hosts, components, notAddedServicesDictionary, true);

  const isServicesMappingEmpty = servicesMapping.length === 0;

  const handleNext = () => {
    onNext({ hostComponentMap: localMapping });
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleMappingFilterChange({ hostName: event.target.value });
  };

  const hasErrors = Object.keys(mappingErrors).length > 0;
  const initiallyMappedHosts = useMemo(() => getInitiallyMappedHostsDictionary(mapping), [mapping]);

  return (
    <div>
      <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
        <SearchInput onChange={handleFilterChange} placeholder="Search host" />
        <ButtonGroup>
          <Button variant="tertiary" iconLeft="g1-return" onClick={handleReset} title="Reset" />
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleNext} disabled={isServicesMappingEmpty || hasErrors} hasError={false}>
            Next
          </Button>
        </ButtonGroup>
      </ToolbarPanel>

      {loadState === LoadState.Loading && <SpinnerPanel />}

      {loadState === LoadState.Loaded && (
        <div className={s.dynamicActionDialog__componentWrapper}>
          {isServicesMappingEmpty && (
            <div>
              Add services on the{' '}
              <Link className="text-link" to={`/clusters/${clusterId}/services`} onClick={onCancel}>
                services page
              </Link>
            </div>
          )}
          {servicesMapping.flatMap(({ service, componentsMapping }) =>
            componentsMapping.map((componentMapping) => {
              const allowActions = getComponentMapActions(actionDetails, service, componentMapping.component);
              const componentMappingErrors = mappingErrors[componentMapping.component.id];

              const checkComponentMappingAvailability = (component: AdcmMappingComponent) => {
                return checkComponentActionsMappingAvailability(component, allowActions);
              };

              const checkHostMappingAvailability = (host: AdcmHostShortView) => {
                return checkHostActionsMappingAvailability(
                  host,
                  allowActions,
                  initiallyMappedHosts[componentMapping.component.id],
                );
              };

              const checkHostUnmappingAvailability = (host: AdcmHostShortView) => {
                return checkHostActionsUnmappingAvailability(
                  host,
                  allowActions,
                  initiallyMappedHosts[componentMapping.component.id],
                );
              };

              return (
                <ComponentContainer
                  key={componentMapping.component.id}
                  componentMapping={componentMapping}
                  filter={mappingFilter}
                  allHosts={hosts}
                  mappingErrors={componentMappingErrors}
                  onMap={handleMapHostsToComponent}
                  onUnmap={handleUnmap}
                  checkComponentMappingAvailability={checkComponentMappingAvailability}
                  checkHostMappingAvailability={checkHostMappingAvailability}
                  checkHostUnmappingAvailability={checkHostUnmappingAvailability}
                />
              );
            }),
          )}
        </div>
      )}
    </div>
  );
};

export default DynamicActionHostMapping;
