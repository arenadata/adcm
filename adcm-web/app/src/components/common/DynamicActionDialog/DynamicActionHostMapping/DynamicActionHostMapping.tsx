import React, { useEffect } from 'react';
import { useDispatch, useStore } from '@hooks';
import { Button, ButtonGroup, SearchInput, SpinnerPanel, ToolbarPanel } from '@uikit';
import { DynamicActionCommonOptions } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import { useClusterMapping } from '@pages/cluster/ClusterMapping/useClusterMapping';
import ComponentContainer from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainer';
import { AdcmMappingComponent, AdcmMappingComponentService } from '@models/adcm';
import { getMappings } from '@store/adcm/clusters/clustersDynamicActionsSlice';
import { Link } from 'react-router-dom';
import { LoadState } from '@models/loadState';

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
    mappingValidation,
    handleMap,
    handleUnmap,
    handleReset,
  } = useClusterMapping(mapping, hosts, components, notAddedServicesDictionary, true);

  const isServicesMappingEmpty = servicesMapping.length === 0;

  const handleSubmit = () => {
    onSubmit({ hostComponentMap: localMapping });
  };

  const getMapRules = (service: AdcmMappingComponentService, component: AdcmMappingComponent) => {
    return actionDetails.hostComponentMapRules.filter(
      (rule) => rule.service === service.name && rule.component === component.name,
    );
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleMappingFilterChange({ hostName: event.target.value });
  };

  return (
    <div>
      <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
        <SearchInput onChange={handleFilterChange} placeholder="Search host" />
        <ButtonGroup>
          <Button variant="tertiary" iconLeft="g1-return" onClick={handleReset} title="Reset" />
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isServicesMappingEmpty || !mappingValidation.isAllMappingValid}
            hasError={false}
          >
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
              const actions = getMapRules(service, componentMapping.component).map((rule) => rule.action);
              const allowActions = [...new Set(actions)];

              return (
                <ComponentContainer
                  key={componentMapping.component.id}
                  componentMapping={componentMapping}
                  filter={mappingFilter}
                  allHosts={hosts}
                  notAddedServicesDictionary={notAddedServicesDictionary}
                  componentMappingValidation={mappingValidation.byComponents[componentMapping.component.id]}
                  onMap={handleMap}
                  onUnmap={handleUnmap}
                  allowActions={allowActions}
                  denyAddHostReason="Add host do not allow in config of action"
                  denyRemoveHostReason="Remove host do not allow in config of action"
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
