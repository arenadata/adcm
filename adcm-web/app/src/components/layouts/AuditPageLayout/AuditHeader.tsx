import TabsBlock from '@uikit/Tabs/TabsBlock';
import Tab from '@uikit/Tabs/Tab';

const AuditHeader = () => (
  <TabsBlock justify="end" className="ignore-page-padding">
    <Tab to="/audit/operations">Operations</Tab>
    <Tab to="/audit/logins">Logins</Tab>
  </TabsBlock>
);

export default AuditHeader;
