import React, { useCallback, useRef } from 'react';
import MonacoCodeEditor from './MonacoCodeEditor';
import yaml from 'yaml';
import Select from '@uikit/Select/SingleSelect/Select/Select';
import type { JSONObject } from '@models/json';
import type { SelectOption } from '@uikit/Select/Select.types';

type ConfigWithSchemaProps = {
  initLanguage: 'json' | 'yaml';
  initConfig: JSONObject;
  initSchema?: JSONObject;
  modelUri: string;
};

const parse = (text: string, language: string) => {
  if (language === 'json') {
    return JSON.parse(text);
  }
  if (language === 'yaml') {
    return yaml.parse(text);
  }
};

const stringify = (textModel: JSONObject, language: string) => {
  if (language === 'json') {
    return JSON.stringify(textModel, null, 2);
  }
  if (language === 'yaml') {
    const yamlConfig = yaml.parse(JSON.stringify(textModel));
    return yaml.stringify(yamlConfig);
  }
  return '';
};

const selectLanguageOptions: SelectOption<string>[] = [
  { label: 'json', value: 'json' },
  { label: 'yaml', value: 'yaml' },
];

const ConfigWithSchema: React.FC<ConfigWithSchemaProps> = ({ initLanguage, initConfig, initSchema, modelUri }) => {
  const [language, setLanguage] = React.useState<string>(initLanguage);
  const configRef = useRef(initConfig);

  const handleChange = useCallback(
    (value: string) => {
      configRef.current = parse(value, language);
    },
    [language],
  );

  const handleLanguageChange = (value: string | null) => {
    if (value !== null) {
      setLanguage(value);
    }
  };

  return (
    <div>
      <Select value={language} options={selectLanguageOptions} onChange={handleLanguageChange} />
      <br />
      <br />
      <MonacoCodeEditor
        uri={`${modelUri}.${language}`}
        language={language}
        text={stringify(configRef.current, language)}
        schema={initSchema}
        onChange={handleChange}
      />
      {initSchema && (
        <>
          <br />
          <br />
          <h3>JSON-schema for this validation (read only):</h3>
          <br />
          <MonacoCodeEditor
            uri={`${modelUri}_schema.json`}
            language="json"
            text={JSON.stringify(initSchema, null, 2)}
          />
        </>
      )}
    </div>
  );
};

export default ConfigWithSchema;
