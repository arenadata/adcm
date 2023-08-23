import React from 'react';
import ToolbarPanel from '@uikit/ToolbarPanel/ToolbarPanel';
import { Button, ButtonGroup, SearchInput } from '@uikit';
import { DynamicActionCommonOptions } from '@commonComponents/DynamicActionDialog/DynamicAction.types';
import s from '@commonComponents/DynamicActionDialog/DynamicActionDialog.module.scss';
import { useClusterMapping } from '@pages/cluster/ClusterMapping/useClusterMapping';
import ComponentContainer from '@pages/cluster/ClusterMapping/ComponentsMapping/ComponentContainer/ComponentContainer';
import { AdcmComponent, AdcmComponentService } from '@models/adcm';
import { SpinnerPanel } from '@uikit/Spinner/Spinner';

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
  const {
    hostComponentMapping,
    hosts,
    servicesMapping,
    handleServicesMappingFilterChange,
    isValid,
    hasSaveError,
    handleMapHostsToComponent,
    handleUnmap,
    handleRevert,
    isLoading,
    isLoaded,
  } = useClusterMapping(clusterId);

  const handleSubmit = () => {
    onSubmit({ hostComponentMap: hostComponentMapping });
  };

  const getMapRules = (service: AdcmComponentService, component: AdcmComponent) => {
    return actionDetails.hostComponentMapRules.filter(
      (rule) => rule.service === service.name && rule.component === component.name,
    );
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleServicesMappingFilterChange({ hostName: event.target.value });
  };

  return (
    <div>
      <ToolbarPanel className={s.dynamicActionDialog__toolbar}>
        <SearchInput onChange={handleFilterChange} placeholder="Search host" />
        <ButtonGroup>
          <Button variant="secondary" iconLeft="g1-return" onClick={handleRevert} title="Reset" />
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid} hasError={hasSaveError}>
            {submitLabel}
          </Button>
        </ButtonGroup>
      </ToolbarPanel>

      {isLoading && <SpinnerPanel />}

      {isLoaded && (
        <div>
          {servicesMapping.flatMap(({ service, componentsMapping }) =>
            componentsMapping.map((componentMapping) => {
              const actions = getMapRules(service, componentMapping.component).map((rule) => rule.action);
              const allowActions = [...new Set(actions)];

              return (
                <ComponentContainer
                  key={componentMapping.component.id}
                  componentMapping={componentMapping}
                  allHosts={hosts}
                  onMap={handleMapHostsToComponent}
                  onUnmap={handleUnmap}
                  allowActions={allowActions}
                  isDisabled={actions.length === 0}
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
