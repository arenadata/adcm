import TabsBlock from '@uikit/Tabs/TabsBlock';
import Tab from '@uikit/Tabs/Tab';

const AccessManagerHeader = () => (
  <TabsBlock justify="end" className="ignore-page-padding">
    <Tab to="/access-manager/users">Users</Tab>
    <Tab to="/access-manager/groups">Groups</Tab>
    <Tab to="/access-manager/roles">Roles</Tab>
    <Tab to="/access-manager/policy">Policy</Tab>
  </TabsBlock>
);

export default AccessManagerHeader;
