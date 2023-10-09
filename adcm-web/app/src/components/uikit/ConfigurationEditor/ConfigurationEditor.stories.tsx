import { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import ConfigurationEditor from './ConfigurationEditor';
import { schema } from './ConfigurationEditor.stories.constants';
import { ConfigurationAttributes, ConfigurationData } from '@models/adcm';
import { ConfigurationNodeFilter } from './ConfigurationEditor.types';
import { Checkbox, Input } from '@uikit';

type Story = StoryObj<typeof ConfigurationEditor>;
export default {
  title: 'uikit/ConfigurationEditor',
  component: ConfigurationEditor,
} as Meta<typeof ConfigurationEditor>;

const initialConfiguration = {
  cluster_config: {
    cluster: [
      {
        cluster_name: 'Lorem ipsum cluster',
        shard: [
          { internal_replica: 1, replicas: [{ host: 'host111' }], weight: 11 },
          { internal_replica: 2, replicas: [{ host: 'host111' }], weight: 110 },
        ],
      },
    ],
  },
  test_config: {
    someBoolean: false,
    someStringWithDefaultValue: 'user defined value',
    someStringWithSuggestions: 'user defined value',
    someEnum: 2,
    someSecretField: '***secret***',
    someMultilineField:
      'lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum lorem ipsum',
    someJsonField: `{
  "user": {
    "first_name": "john",
    "last_name": "doe",
    "age": 42,
    "driver_license": null,
    "is_fake": true
  }
}`,
    someYamlField: `- name: my_boolean
  type: boolean
  required: false
  default: true
  read_only: any`,
    someReadOnlyField: 'read only field',
    someAnyOfField: null,
    someInvisibleField: 'must be invisible',
    someAdvancedField: 'advanced',
    someMap: {
      key1: 'value1',
    },
    someSecretMap: {},
    someReadOnlyMap: {
      key1: 'value1',
    },
  },
};

const initialAttributes: ConfigurationAttributes = {
  '/cluster_config/cluster': {
    isActive: true,
    isSynchronized: true,
  },
  '/test_config': {
    isActive: false,
    isSynchronized: false,
  },
};

const ConfigurationEditorStoryWithHooks = () => {
  const [configuration, setConfiguration] = useState<ConfigurationData>(initialConfiguration);
  const [attributes, setAttributes] = useState<ConfigurationAttributes>(initialAttributes);
  const [filter, setFilter] = useState<ConfigurationNodeFilter>({
    title: '',
    showAdvanced: false,
    showInvisible: false,
  });

  const handleConfigurationChange = (configuration: ConfigurationData) => {
    console.info(configuration);
    setConfiguration(configuration);
  };

  const handleAttributesChange = (attributes: ConfigurationAttributes) => {
    console.info(attributes);
    setAttributes(attributes);
  };

  const handleAdvancedChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilter((prevFilter) => ({ ...prevFilter, showAdvanced: event.target.checked }));
  };

  const handleInvisibleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilter((prevFilter) => ({ ...prevFilter, showInvisible: event.target.checked }));
  };

  const handleFilterChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setFilter((prevFilter) => ({ ...prevFilter, title: event.target.value }));
  };

  return (
    <>
      Show advanced:
      <Checkbox checked={filter.showAdvanced} onChange={handleAdvancedChange} />
      <br />
      Show invisible:
      <Checkbox checked={filter.showInvisible} onChange={handleInvisibleChange} />
      <br />
      Filter:
      <Input value={filter.title} onChange={handleFilterChange} />
      <br />
      <ConfigurationEditor
        schema={schema}
        configuration={configuration}
        attributes={attributes}
        filter={filter}
        onConfigurationChange={handleConfigurationChange}
        onAttributesChange={handleAttributesChange}
      />
    </>
  );
};

export const ConfigurationEditorStory: Story = {
  render: () => <ConfigurationEditorStoryWithHooks />,
};
