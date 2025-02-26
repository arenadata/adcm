import MonacoCodeEditor from '@uikit/MonacoCodeEditor/MonacoCodeEditor';
import type { IPosition, ITextModel } from '@uikit/MonacoCodeEditor/MonacoCodeEditor.types';
import yaml from 'yaml';
import { useCallback, useRef } from 'react';
import { mappingSchema, mappingText, mappingUrl } from './MappingConfigEditor.constants';
import type { AdcmHostShortView, AdcmMappingComponent } from '@models/adcm';
import {
  generateComponentsProposals,
  generateHostsProposals,
  generateServicesProposals,
} from './MappingConfigEditor.utils';
import type { JSONObject } from '@models/json';

interface MappingConfigEditorProps {
  hosts: AdcmHostShortView[];
  components: AdcmMappingComponent[];
}

const MappingConfigEditor = ({ hosts, components }: MappingConfigEditorProps) => {
  const model = useRef<JSONObject>({});

  const handleChange = useCallback((value: string) => {
    try {
      const parsed = yaml.parse(value) as JSONObject;
      model.current = parsed;
    } catch (e) {
      console.error('mapping parse error', e);
    }
  }, []);

  const handleAutoComplete = useCallback(
    (model: ITextModel, position: IPosition) => {
      // find out if we are completing a property in the 'dependencies' object.
      const line = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      });

      const matches = line.match(/^[\s]*/g);
      if (matches === null) {
        return [];
      }

      const word = model.getWordUntilPosition(position);
      const spacesCount = matches[0].length;

      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      switch (spacesCount) {
        case 2:
          return generateServicesProposals(components, range);
        case 4:
          return generateComponentsProposals(components, range);
        case 6:
          return generateHostsProposals(hosts, range);
        default:
          return [];
      }
    },
    [hosts, components],
  );

  return (
    <MonacoCodeEditor
      uri={mappingUrl}
      language="yaml"
      text={mappingText}
      schema={mappingSchema}
      onAutoComplete={handleAutoComplete}
      onChange={handleChange}
    />
  );
};

export default MappingConfigEditor;
