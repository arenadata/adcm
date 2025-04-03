import MonacoCodeEditor from './MonacoCodeEditor';
import type { Meta, StoryObj } from '@storybook/react';
import {
  adcmConfig,
  adcmAttributes,
  adcmConfigurationSchema,
  adcmSwappedAttributes,
} from './MonacoCodeEditor.adcm.stories.constants';
import AdcmConfigEditor from './adcm/AdcmConfigEditor';
import { swapAll } from './adcm/AdcmConfigEditor.utils';
import { ConfigurationEditorStoryWithHooks } from '@uikit/ConfigurationEditor/ConfigurationEditor.stories';

type Story = StoryObj<typeof MonacoCodeEditor>;

export default {
  title: 'uikit/MonacoCodeEditor_ADCM',
  component: MonacoCodeEditor,
  argTypes: {},
} as Meta<typeof MonacoCodeEditor>;

export const AdcmConfigEditorPlainYamlStory: Story = {
  args: {},
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <AdcmConfigEditor schema={adcmConfigurationSchema} config={adcmConfig} attributes={adcmAttributes} />
      </div>
    );
  },
};

export const AdcmConfigEditorPlainYamlWithCommentsStory: Story = {
  args: {},
  render: () => {
    return (
      <div style={{ height: '500px' }}>
        <AdcmConfigEditor
          schema={adcmConfigurationSchema}
          config={adcmConfig}
          attributes={adcmAttributes}
          autoApplyComments={true}
        />
      </div>
    );
  },
};

export const AdcmConfigEditorSwappedYamlStory: Story = {
  args: {},
  render: () => {
    const { schema, config, attributes } = swapAll(adcmConfigurationSchema, adcmConfig, adcmSwappedAttributes);
    return (
      <div style={{ height: '500px' }}>
        <AdcmConfigEditor schema={schema} config={config} attributes={attributes} />
      </div>
    );
  },
};

export const AdcmConfigEditorTreeStory: Story = {
  render: () => (
    <ConfigurationEditorStoryWithHooks
      schema={adcmConfigurationSchema}
      initialConfigurationData={adcmConfig}
      initialAttributes={adcmAttributes}
    />
  ),
};
