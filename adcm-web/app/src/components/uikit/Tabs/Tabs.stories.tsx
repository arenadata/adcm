/* eslint-disable spellcheck/spell-checker */
import React from 'react';
import { Meta, StoryObj } from '@storybook/react';
import TabsBlock, { TabsBlockProps } from '@uikit/Tabs/TabsBlock';
import Tab from '@uikit/Tabs/Tab';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import Icon from '@uikit/Icon/Icon';
import Statusable from '@uikit/Statusable/Statusable';

const pageStyles = {
  marginTop: '30px',
  fontSize: '30px',
  lineHeight: '2em',
  color: 'var(--color-xgreen)',
};

const easyTabsPages = [
  {
    path: '/home',
    content: 'Home',
  },
  {
    path: '/about',
    content: 'About',
  },
  {
    path: '/page1',
    content: 'Page1',
  },
  {
    path: '/page2',
    content: 'Page2',
  },
];

type Story = StoryObj<typeof TabsBlock>;
export default {
  title: 'uikit/Tabs',
  component: TabsBlock,
  decorators: [
    (Story, context) => {
      return (
        <MemoryRouter
          initialEntries={context.parameters.pages.map(({ path }: { path: string }) => path)}
          initialIndex={0}
        >
          <Story />
          <Routes>
            {context.parameters.pages.map(({ path, content }: { path: string; content: string }) => (
              <Route path={path} element={<div style={pageStyles}>{content}</div>} key={path} />
            ))}
          </Routes>
        </MemoryRouter>
      );
    },
  ],
  argTypes: {
    children: {
      table: {
        disable: true,
      },
    },
    variant: {
      table: {
        disable: true,
      },
    },
  },
} as Meta<typeof TabsBlock>;

const EasyTabsExample: React.FC<TabsBlockProps> = (args) => {
  return (
    <div>
      <TabsBlock {...args}>
        <Tab to="/home">Home</Tab>
        <Tab to="/about">About</Tab>
        <Tab to="/page1">Page 1</Tab>
        <Tab to="/page2">Page 2</Tab>
      </TabsBlock>
      <Outlet />
    </div>
  );
};

export const PrimaryTabs: Story = {
  parameters: {
    pages: easyTabsPages,
  },
  args: {
    variant: 'primary',
  },
  render: (args) => {
    return <EasyTabsExample {...args} />;
  },
};

export const SecondaryTabs: Story = {
  parameters: {
    pages: easyTabsPages,
  },
  args: {
    variant: 'secondary',
  },
  render: (args) => {
    return <EasyTabsExample {...args} />;
  },
};

const ClusterTabsExample: React.FC<TabsBlockProps> = (args) => {
  return (
    <div>
      <TabsBlock {...args}>
        <div style={{ flex: '1', display: 'flex', alignItems: 'center' }}>
          <div style={{ color: 'var(--color-xgreen)', fontSize: '18px', lineHeight: '21px', fontWeight: 500 }}>
            Cluster Name
          </div>
          <Icon name="g1-actions" size={24} style={{ color: 'var(--color-xgray-light)' }} />
        </div>
        <Tab to="/overview">Overview</Tab>
        <Tab to="/services">Services</Tab>
        <Tab to="/hosts">Hosts</Tab>
        <Tab to="/mapping">
          <Statusable status="unknown">Mapping</Statusable>
        </Tab>
        <Tab to="/configuration">Configuration</Tab>
        <Tab to="/import">Import</Tab>
      </TabsBlock>
      <Outlet />
    </div>
  );
};

export const ComplexTabs: Story = {
  parameters: {
    pages: [
      {
        path: '/overview',
        content: 'Overview',
      },
      {
        path: '/services',
        content: 'Services',
      },
      {
        path: '/hosts',
        content: 'Hosts',
      },
      {
        path: '/mapping',
        content: 'Mapping',
      },
      {
        path: '/configuration',
        content: 'Configuration',
      },
      {
        path: '/import',
        content: 'Import',
      },
    ],
  },
  args: {
    variant: 'primary',
  },
  render: (args) => {
    return <ClusterTabsExample {...args} />;
  },
};
