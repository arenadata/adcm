import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import ConfigurationEditor from './ConfigurationEditor';
import {
  clusterConfigurationSchema,
  initialClusterConfiguration,
  complexSchema,
  readOnlyConfig,
  readOnlySchema,
  nullableConfig,
  nullableSchema,
} from './ConfigurationEditor.stories.constants';
import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import type { ConfigurationTreeFilter } from './ConfigurationEditor.types';
import { Checkbox, Input, Switch } from '@uikit';
import { generateFromSchema } from '@utils/jsonSchema/jsonSchemaUtils';

type Story = StoryObj<typeof ConfigurationEditor>;
export default {
  title: 'uikit/ConfigurationEditor',
  component: ConfigurationEditor,
  excludeStories: ['ConfigurationEditorStoryWithHooks'],
} as Meta<typeof ConfigurationEditor>;

// const initialAttributes: ConfigurationAttributes = {
//   '/cluster_config/cluster': {
//     isActive: true,
//     isSynchronized: true,
//   },
//   '/test_config': {
//     isActive: false,
//     isSynchronized: false,
//   },
//   '/test_config/someMapWithAttributes': {
//     isActive: false,
//     isSynchronized: false,
//   },
//   '/test_config/someMapWithAttributes/key1': {
//     isActive: false,
//     isSynchronized: false,
//   },
//   '/readonly_props/someSyncString': {
//     isActive: false,
//     isSynchronized: true,
//   },
//   '/readonly_props/someSyncMap': {
//     isActive: false,
//     isSynchronized: true,
//   },
// };

interface StoryProps {
  initialConfigurationData: ConfigurationData | null;
  initialAttributes: ConfigurationAttributes | null;
  schema: ConfigurationSchema;
}

export const ConfigurationEditorStoryWithHooks = ({
  initialConfigurationData,
  initialAttributes,
  schema,
}: StoryProps) => {
  const safeConfigurationData = initialConfigurationData ?? generateFromSchema(schema);
  // biome-ignore lint/suspicious/noExplicitAny:
  const [configuration, setConfiguration] = useState<ConfigurationData>(safeConfigurationData as any);
  const [attributes, setAttributes] = useState<ConfigurationAttributes>(initialAttributes ?? {});
  const [areExpandedAll, setAreExpandedAll] = useState(false);
  const [filter, setFilter] = useState<ConfigurationTreeFilter>({
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

  const handleChangeExpandedAll = () => {
    setAreExpandedAll((prev) => !prev);
  };

  return (
    <>
      <Switch isToggled={filter.showAdvanced} variant="blue" onChange={handleAdvancedChange} label="Show advanced" />
      <Switch isToggled={areExpandedAll} onChange={handleChangeExpandedAll} label="expand content" />
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
        areExpandedAll={areExpandedAll}
        onConfigurationChange={handleConfigurationChange}
        onAttributesChange={handleAttributesChange}
      />
    </>
  );
};

export const ConfigurationEditorStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={clusterConfigurationSchema}
      initialConfigurationData={initialClusterConfiguration}
      initialAttributes={null}
    />
  ),
};

export const ConfigurationEditorWithEmptyConfigurationStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={clusterConfigurationSchema}
      initialConfigurationData={null}
      initialAttributes={null}
    />
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

export const ConfigurationEditorWithNullableMapStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={nullableSchema}
      initialConfigurationData={nullableConfig}
      initialAttributes={null}
    />
  ),
};

export const ConfigurationEditorReadonlyStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={readOnlySchema}
      initialConfigurationData={readOnlyConfig}
      initialAttributes={null}
    />
  ),
};

const attributes: ConfigurationAttributes = {
  '/cluster_config/cluster': {
    isActive: true,
    isSynchronized: false,
  },
};

export const ConfigurationEditorAttributesStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={clusterConfigurationSchema}
      initialConfigurationData={initialClusterConfiguration}
      initialAttributes={attributes}
    />
  ),
};

export const ConfigurationEditorDragNDropStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={clusterConfigurationSchema}
      initialConfigurationData={initialClusterConfiguration}
      initialAttributes={attributes}
    />
  ),
};
