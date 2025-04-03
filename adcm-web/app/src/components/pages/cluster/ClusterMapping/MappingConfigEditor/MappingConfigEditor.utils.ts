import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import { type IRange, monaco } from '@uikit/MonacoCodeEditor/MonacoCodeEditor.types';

export const generateServicesProposals = (components: AdcmMappingComponent[], range: IRange) => {
  const processed = new Set<number>();
  const result = [];

  for (const c of components) {
    if (!processed.has(c.service.id)) {
      result.push({
        label: c.service.displayName,
        kind: monaco.languages.CompletionItemKind.Function,
        documentation: c.service.displayName,
        insertText: `${c.service.displayName}:`,
        range: range,
      });

      processed.add(c.service.id);
    }
  }

  return result;
};

export const generateComponentsProposals = (components: AdcmMappingComponent[], range: IRange) => {
  const result = components.map((c) => ({
    label: c.displayName,
    kind: monaco.languages.CompletionItemKind.Function,
    documentation: c.displayName,
    insertText: `${c.displayName}:`,
    range: range,
  }));

  return result;
};

export const generateHostsProposals = (hosts: AdcmHostShortView[], range: IRange) => {
  const result = hosts.map((h) => ({
    label: `${h.name} (maintenance mode ${h.maintenanceMode ? 'on' : 'off'})`,
    kind: monaco.languages.CompletionItemKind.Function,
    documentation: `h.name (maintenance mode is ${h.maintenanceMode ? 'on' : 'off'})`,
    insertText: `- ${h.name}`,
    range: range,
  }));

  result.push({
    label: 'all',
    kind: monaco.languages.CompletionItemKind.Function,
    documentation: 'All hosts',
    insertText: result.map((s) => `- ${s.label}`).join('\n'),
    range: range,
  });

  return result;
};
