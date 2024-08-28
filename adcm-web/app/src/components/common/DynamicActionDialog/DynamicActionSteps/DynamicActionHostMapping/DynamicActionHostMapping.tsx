import React, { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useDispatch, useStore } from '@hooks';
import { Button, ButtonGroup, SearchInput, SpinnerPanel, ToolbarPanel } from '@uikit';
import { useClusterMapping } from '@pages/cluster/ClusterMapping/useClusterMapping';
import ComponentContainer from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainer';
import { getMappings } from '@store/adcm/entityDynamicActions/dynamicActionsMappingSlice';
import { getComponentMapActions, getDisabledMappings } from './DynamicActionHostMapping.utils';
import { LoadState } from '@models/loadState';
import type { AdcmDynamicActionDetails, AdcmDynamicActionRunConfig } from '@models/adcm';
import s from '../..//DynamicActionDialog.module.scss';

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
          <Button onClick={handleNext} disabled={isServicesMappingEmpty || hasErrors} hasError={false}>
            Next
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

              return (
                <ComponentContainer
                  key={componentMapping.component.id}
                  componentMapping={componentMapping}
                  filter={mappingFilter}
                  allHosts={hosts}
                  disabledHosts={disabledMappings[componentMapping.component.id]}
                  mappingErrors={componentMappingErrors}
                  onMap={handleMapHostsToComponent}
                  onUnmap={handleUnmap}
                  allowActions={allowActions}
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
