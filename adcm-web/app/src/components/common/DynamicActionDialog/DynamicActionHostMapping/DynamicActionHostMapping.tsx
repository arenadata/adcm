import React, { useEffect, useMemo } from 'react';
import { useDispatch, useStore } from '@hooks';
import { Button, ButtonGroup, SearchInput, SpinnerPanel, ToolbarPanel } from '@uikit';
import type { DynamicActionCommonOptions } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import { useClusterMapping } from '@pages/cluster/ClusterMapping/useClusterMapping';
import ComponentContainer from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainer';
import { getMappings } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import {
  checkComponentActionsMappingAvailability,
  checkHostActionsMappingAvailability,
  getComponentMapActions,
  getDisabledMappings,
} from './DynamicActionHostMapping.utils';
import { Link } from 'react-router-dom';
import { LoadState } from '@models/loadState';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';

interface DynamicActionHostMappingProps extends DynamicActionCommonOptions {
  submitLabel?: string;
  clusterId: number;
}

const DynamicActionHostMapping: React.FC<DynamicActionHostMappingProps> = ({
  clusterId,
  actionDetails,
  onSubmit,
  onCancel,
  submitLabel = 'Run',
}) => {
  const dispatch = useDispatch();

  useEffect(() => {
    if (!Number.isNaN(clusterId)) {
      dispatch(getMappings({ clusterId }));
    }
  }, [clusterId, dispatch]);

  const {
    dialog: { hosts, components, mapping, loadState },
  } = useStore(({ adcm }) => adcm.clustersDynamicActions);

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

  const handleSubmit = () => {
    onSubmit({ hostComponentMap: localMapping });
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleMappingFilterChange({ hostName: event.target.value });
  };

  const hasErrors = Object.keys(mappingErrors).length > 0;
  const disabledMappings = useMemo(() => getDisabledMappings(mapping), [mapping]);

  return (
    <div>
      <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
        <SearchInput onChange={handleFilterChange} placeholder="Search host" />
        <ButtonGroup>
          <Button variant="tertiary" iconLeft="g1-return" onClick={handleReset} title="Reset" />
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={isServicesMappingEmpty || hasErrors} hasError={false}>
            {submitLabel}
          </Button>
        </ButtonGroup>
      </ToolbarPanel>

      {loadState === LoadState.Loading && <SpinnerPanel />}

      {loadState === LoadState.Loaded && (
        <div>
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
                  disabledMappings[componentMapping.component.id],
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
