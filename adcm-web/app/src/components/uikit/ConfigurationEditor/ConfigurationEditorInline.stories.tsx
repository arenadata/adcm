import { useState } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import ConfigurationEditor from './ConfigurationEditor';
import {
  inlineEditConfigurationData,
  inlineEditConfigurationSchema,
} from './ConfigurationEditorInline.stories.constants';
import type { ConfigurationAttributes, ConfigurationData, ConfigurationSchema } from '@models/adcm';
import type { ConfigurationTreeFilter } from './ConfigurationEditor.types';
import { Checkbox, Input, Switch } from '@uikit';
import CodeHighlighter from '@uikit/CodeHighlighter/CodeHighlighter';
import s from './ConfigurationEditorInline.stories.module.scss';

type Story = StoryObj<typeof ConfigurationEditor>;

export default {
  title: 'uikit/ConfigurationEditor/Inline edit',
  component: ConfigurationEditor,
} as Meta<typeof ConfigurationEditor>;

interface InlineEditStoryProps {
  initialConfigurationData: ConfigurationData;
  schema: ConfigurationSchema;
  initialAttributes?: ConfigurationAttributes;
}

const ConfigurationEditorInlineStory = ({
  initialConfigurationData,
  schema,
  initialAttributes = {},
}: InlineEditStoryProps) => {
  const [configuration, setConfiguration] = useState<ConfigurationData>(initialConfigurationData);
  const [attributes, setAttributes] = useState<ConfigurationAttributes>(initialAttributes);
  const [areExpandedAll, setAreExpandedAll] = useState(true);
  const [filter, setFilter] = useState<ConfigurationTreeFilter>({
    title: '',
    showAdvanced: true,
    showInvisible: false,
  });

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
    <div className={s.story}>
      <div className={s.story__toolbar}>
        <Switch isToggled={filter.showAdvanced} variant="blue" onChange={handleAdvancedChange} label="Show advanced" />
        <Switch isToggled={areExpandedAll} onChange={handleChangeExpandedAll} label="Expand all" />
        <label>
          Show invisible:
          <Checkbox checked={filter.showInvisible} onChange={handleInvisibleChange} />
        </label>
        <label>
          Filter:
          <Input value={filter.title} onChange={handleFilterChange} />
        </label>
      </div>
      <div className={s.story__content}>
        <div className={s.story__editor}>
          <ConfigurationEditor
            schema={schema}
            configuration={configuration}
            attributes={attributes}
            filter={filter}
            areExpandedAll={areExpandedAll}
            onConfigurationChange={setConfiguration}
            onAttributesChange={setAttributes}
            onConfigurationAndAttributesChange={(nextConfiguration, nextAttributes) => {
              setConfiguration(nextConfiguration);
              setAttributes(nextAttributes);
            }}
          />
        </div>
        <div className={s.story__state}>
          <div className={s.story__stateTitle}>Current configuration</div>
          <CodeHighlighter code={JSON.stringify(configuration, null, 2)} language="json" />
        </div>
      </div>
    </div>
  );
};

export const PrimitiveFieldsStory: Story = {
  render: () => (
    <ConfigurationEditorInlineStory
      schema={inlineEditConfigurationSchema}
      initialConfigurationData={inlineEditConfigurationData}
    />
  ),
};
