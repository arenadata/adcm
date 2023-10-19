import { useState } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import ConfigurationEditor from './ConfigurationEditor';
import { schema, complexSchema } from './ConfigurationEditor.stories.constants';
import { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import { ConfigurationNodeFilter } from './ConfigurationEditor.types';
import { Checkbox, Input, Switch } from '@uikit';
import { generateFromSchema } from '@utils/jsonSchemaUtils';

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
  readonly_props: {
    someBoolean: true,
    someString: 'user defined value',
    someNumber: 111,
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
    someAnyOfField: null,
    someInvisibleField: 'must be invisible',
    someAdvancedField: 'advanced',
    someMap: {
      key1: 'value1',
    },
    someSecretMap: {
      key1: 'value1',
    },
    someSyncString: 'sync string',
    someSyncMap: {
      key1: 'value',
    },
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
    someAnyOfField: null,
    someInvisibleField: 'must be invisible',
    someAdvancedField: 'advanced',
    someMap: {
      key1: 'value1',
    },
    someSecretMap: {
      key1: 'value1',
    },
    someMapWithAttributes: {
      key1: 'value',
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
  '/test_config/someMapWithAttributes': {
    isActive: false,
    isSynchronized: false,
  },
  '/test_config/someMapWithAttributes/key1': {
    isActive: false,
    isSynchronized: false,
  },
  '/readonly_props/someSyncString': {
    isActive: false,
    isSynchronized: true,
  },
  '/readonly_props/someSyncMap': {
    isActive: false,
    isSynchronized: true,
  },
};

interface StoryProps {
  initialConfigurationData: ConfigurationData | null;
  initialAttributes: ConfigurationAttributes | null;
  schema: ConfigurationSchema;
}

const ConfigurationEditorStoryWithHooks = ({
  initialConfigurationData: initialConfiguration,
  initialAttributes,
  schema,
}: StoryProps) => {
  const safeConfigurationData = initialConfiguration ?? generateFromSchema(schema);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [configuration, setConfiguration] = useState<ConfigurationData>(safeConfigurationData as any);
  const [attributes, setAttributes] = useState<ConfigurationAttributes>(initialAttributes ?? {});
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
      <Switch isToggled={filter.showAdvanced} variant="blue" onChange={handleAdvancedChange} label="Show advanced" />
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
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={schema}
      initialConfigurationData={initialConfiguration}
      initialAttributes={initialAttributes}
    />
  ),
};

export const ConfigurationEditorWithEmptyConfigurationStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks schema={schema} initialConfigurationData={null} initialAttributes={null} />
  ),
};

export const ConfigurationEditorWithComplexConfigurationStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={complexSchema}
      initialConfigurationData={null}
      initialAttributes={null}
    />
  ),
};
