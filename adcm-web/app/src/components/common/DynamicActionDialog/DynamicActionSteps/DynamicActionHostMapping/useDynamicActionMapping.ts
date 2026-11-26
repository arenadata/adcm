import { useMemo } from 'react';
import type {
  AdcmDynamicActionDetails,
  AdcmHostShortView,
  AdcmMapping,
  AdcmMappingComponent,
  NotAddedServicesDictionary,
} from '@models/adcm';
import { useMappingEditor } from '@hooks/useMappingEditor';
import type { MappingActionRule, MappingViewConfig } from '@utils/mapping/mapping.types';

export const useDynamicActionMapping = (
  mapping: AdcmMapping[],
  hosts: AdcmHostShortView[],
  components: AdcmMappingComponent[],
  notAddedServicesDictionary: NotAddedServicesDictionary,
  isLoaded: boolean,
  actionDetails: AdcmDynamicActionDetails,
) => {
  const { viewConfig, actionRules } = useMemo((): {
    viewConfig: MappingViewConfig;
    actionRules: MappingActionRule[];
  } => {
    const actionRules: MappingActionRule[] = (actionDetails.hostComponentMapRules ?? []).map((rule) => ({
      service: rule.service,
      component: rule.component,
      operation: rule.action,
    }));

    return {
      actionRules,
      viewConfig: {
        strategy: {
          type: 'actionRules',
          rules: actionRules,
        },
        kind: 'flat',
        sort: 'editableFirst',
      },
    };
  }, [actionDetails.hostComponentMapRules]);

  const editor = useMappingEditor(mapping, hosts, components, notAddedServicesDictionary, isLoaded, viewConfig);

  const flatComponents = editor.viewModel?.kind === 'flat' ? editor.viewModel.components : [];

  return {
    ...editor,
    flatComponents,
    actionRules,
  };
};
