import AnchorBar, { AnchorList } from './AnchorBar';
import { Meta, StoryObj } from '@storybook/react';
import s from './AnchorBar.stories.module.scss';

interface TestItems {
  id: string;
  content: string;
  label: string;
  colorClass?: string;
}

const testItemsGroups: TestItems[] = [
  {
    id: 'lorem_0',
    content: `
      Lorem ipsum dolor sit amet, consectetur adipiscing elit. Phasellus tincidunt, mi in consectetur molestie, neque odio lacinia massa, et fermentum turpis justo facilisis odio. Morbi feugiat auctor ornare. Curabitur sagittis eros sit amet egestas convallis. Pellentesque interdum magna massa, ac dignissim dolor facilisis a. Aenean eget cursus nisl. Sed pharetra laoreet ligula, ac venenatis felis dapibus at. Ut a vehicula risus, aliquam rutrum orci. Fusce ornare, tellus et venenatis consequat, arcu nisl commodo sapien, non molestie nibh neque quis dolor. Ut felis quam, ultricies at erat sit amet, gravida fringilla est. Vestibulum in fermentum nisl, in porta quam. Phasellus nec pharetra dui, ultricies semper nibh. Curabitur tincidunt dui ante, et fringilla felis molestie ut. Aliquam bibendum a mauris non condimentum. Praesent semper orci nec eros eleifend porttitor. Quisque non condimentum massa. Aliquam tempor pellentesque finibus.
      Mauris sit amet malesuada eros. Sed sed eros non sapien sollicitudin eleifend. Donec ac mi purus. Sed et ligula efficitur, pretium eros quis, feugiat erat. Donec facilisis luctus urna, et varius enim luctus id. Vestibulum id ullamcorper quam. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Ut ornare magna a est tristique posuere. Proin dignissim, tortor eget porta egestas, eros justo viverra ipsum, vel pretium nulla eros eu lorem. Nam quis lobortis metus.
      Nulla imperdiet diam finibus vulputate lacinia. Fusce eleifend aliquet sapien, quis vestibulum neque. Phasellus aliquam dictum quam, mattis eleifend dui mattis a. Etiam sapien libero, viverra eget imperdiet ut, eleifend a nibh. Proin feugiat, eros ut consectetur sagittis, ipsum ligula feugiat nunc, ut sollicitudin mi diam ac mauris. In accumsan justo sed nisi mollis, sit amet malesuada purus iaculis. Sed non ex et urna laoreet porttitor a vitae urna. Praesent eleifend facilisis feugiat. Duis in erat eu nulla tincidunt vestibulum nec quis ligula. Curabitur vel mattis orci. Sed vitae euismod massa, non rutrum sapien. Sed tristique ultricies risus, convallis accumsan mi accumsan non. Nunc auctor varius elementum.
      Quisque eget sapien a libero pellentesque vulputate in sed ex. Nunc consequat interdum auctor. Etiam lacinia sem vitae cursus euismod. Pellentesque a massa vitae leo egestas facilisis eu gravida tortor. Nam aliquet bibendum lacus vitae tincidunt. Vivamus sed lobortis ligula. Vivamus lacinia euismod lorem eu ultrices. Maecenas ut aliquet metus. Praesent porttitor ex ut ultricies scelerisque. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nunc ullamcorper ante vel sem elementum, et feugiat ante posuere.
      Nulla auctor ipsum sed libero tempor, non lacinia libero porttitor. Praesent lobortis urna lorem, quis tempus neque lobortis at. Nulla sed tellus felis. Praesent mollis quam ut magna faucibus viverra in sit amet arcu. Vivamus volutpat mauris id elit mollis, ac vulputate ex venenatis. Fusce eros ligula, lobortis sed sagittis ac, tincidunt eget mi. Pellentesque commodo erat sit amet augue finibus auctor. Sed in ligula suscipit, aliquam elit ut, posuere elit. Fusce sed massa vitae tellus tincidunt condimentum. Cras quis tempus neque. Suspendisse potenti. Vestibulum suscipit nunc vitae nulla imperdiet faucibus.
    `,
    label: 'Cloud',
  },
  {
    id: 'viverra_1',
    content: `
      Sed viverra sagittis commodo. Praesent ut vehicula diam. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Donec suscipit lectus in ligula pulvinar aliquam. Proin a iaculis lacus, in vehicula nisl. Maecenas eget nunc sagittis lectus cursus maximus sit amet eu risus. Donec vitae semper nunc. Nullam iaculis tellus nec libero fermentum elementum. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec et sem ultricies, scelerisque nisl quis, pellentesque eros. Aenean et lacus tincidunt, semper enim eu, semper ipsum. Phasellus dictum gravida dignissim.
      Donec elementum ex et ex malesuada, vel porttitor diam rutrum. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Interdum et malesuada fames ac ante ipsum primis in faucibus. Quisque finibus lectus metus, eu consectetur quam dapibus eu. Morbi eu ligula vel diam malesuada hendrerit. Aliquam semper, dui vitae gravida ornare, nunc mauris dignissim ipsum, a euismod diam tellus et massa. Pellentesque turpis nisi, consectetur vel elit quis, congue fermentum sapien. Proin varius massa eu libero congue, ac volutpat magna consequat. Nulla ac lorem nulla. Nam vel purus dui. Vivamus vulputate justo quis diam lacinia lobortis. Vestibulum eget tincidunt mauris.
      Vestibulum enim orci, pretium sed erat bibendum, mattis viverra nisi. Donec dictum aliquam congue. Cras eu sem volutpat, interdum risus non, vehicula quam. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Praesent fermentum ante eget convallis luctus. Integer ac rutrum metus, quis condimentum nunc. Sed iaculis fringilla nisi eget sodales. Curabitur cursus ut elit vel molestie.
      Aenean feugiat rhoncus sagittis. Aenean condimentum nunc sed leo sagittis tristique. Nullam in turpis pellentesque, condimentum leo ut, consectetur purus. Cras sed mauris non est finibus vestibulum. Donec nec pulvinar turpis, et sodales dui. Phasellus ut urna gravida, bibendum lectus vitae, rhoncus lorem. Morbi faucibus orci et turpis aliquet maximus. In hac habitasse platea dictumst. Nulla lobortis nunc et sem luctus ultrices. In vestibulum eget justo non finibus. Suspendisse in accumsan tortor. Vivamus mattis augue vel ante pharetra molestie. Vivamus dapibus tortor sapien, quis accumsan tellus ultrices ac. Vivamus maximus ante id urna hendrerit porttitor. Praesent ullamcorper lorem sed turpis viverra sollicitudin.
      Morbi sagittis porta eros non efficitur. Integer eget augue ut ligula ultricies consequat. Vivamus nibh mauris, iaculis quis magna sit amet, sagittis rutrum quam. Aliquam non dui vitae magna viverra pretium. Etiam eros leo, pharetra ut enim vitae, tincidunt vehicula lacus. Cras feugiat nisi ac turpis sagittis, eget ornare elit viverra. Aenean mi nunc, bibendum eu neque id, vestibulum pretium sem. Sed blandit lobortis justo, a suscipit eros bibendum consectetur. Vivamus in pretium ipsum. Vestibulum nisi risus, placerat non metus eu, maximus viverra purus. Vestibulum faucibus congue orci. Quisque nec odio eu tellus pellentesque congue. Nunc vel iaculis diam, pellentesque cursus nibh. Sed sed magna tincidunt, pharetra justo eget, cursus tellus. Duis quis erat eros.
      Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Nunc sagittis libero in congue venenatis. Fusce ultrices consectetur luctus. Aenean et justo in enim lacinia molestie. Morbi urna lacus, tincidunt volutpat facilisis vitae, fermentum vel justo. Pellentesque tincidunt diam in nibh molestie ornare. Quisque convallis ipsum ut dolor dapibus fermentum.
      Mauris condimentum consectetur quam quis mattis. Interdum et malesuada fames ac ante ipsum primis in faucibus. Curabitur in mauris ut dolor volutpat pulvinar vitae non massa. Cras nisl sem, sodales in rhoncus sollicitudin, gravida vitae orci. Cras quis interdum sapien. In dapibus nulla tortor, ac vulputate ipsum convallis in. Nunc a felis ac magna congue hendrerit. Duis laoreet lacus ac purus venenatis, a blandit velit semper.
      Aenean ante sem, dignissim nec ultrices sit amet, consequat sed sapien. Interdum et malesuada fames ac ante ipsum primis in faucibus. Aliquam accumsan quam leo, id aliquam sem laoreet eget. Vivamus in egestas nunc. In nec elementum tortor. Donec mollis feugiat dolor. Sed nisl nisi, condimentum vitae augue vel, consequat eleifend mi. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed sit amet consectetur augue. Donec pharetra neque enim. Maecenas vehicula venenatis elit at lacinia. Mauris quis viverra sapien. Aliquam facilisis, purus in tincidunt tempus, quam velit feugiat lectus, volutpat ultricies ante enim id ex. Vestibulum scelerisque, nibh vel malesuada tincidunt, velit magna vulputate mauris, a bibendum nulla dui tempus risus.
    `,
    label: 'Metadata',
  },
  {
    id: 'suspendisse_2',
    content: `
      Suspendisse pellentesque diam non sem tristique ornare. Sed dignissim tempor augue, ac dapibus nunc viverra vel. Cras sagittis egestas leo, at aliquet turpis porttitor at. Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Aenean imperdiet enim hendrerit mattis hendrerit. In volutpat a purus elementum hendrerit. Donec at lobortis purus. Sed semper odio a risus blandit, eget luctus ex consectetur. Sed vitae rutrum dui. Donec in arcu lacus.
      Fusce sollicitudin posuere eros at commodo. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Sed at nibh congue nunc condimentum interdum vitae vitae libero. Phasellus id vehicula lectus. Pellentesque in erat eget purus consequat molestie. Suspendisse sed ante metus. Mauris eu felis mauris. Morbi imperdiet, massa sit amet eleifend molestie, lectus justo molestie nibh, scelerisque scelerisque sem metus vitae tellus. Sed ornare convallis nulla vel ultricies. Maecenas vitae ornare sapien, ac accumsan lectus. Etiam fermentum ornare vulputate.
    `,
    label: 'Default host setting',
  },
  {
    id: 'curabitur_3',
    content: `
      Curabitur tortor augue, blandit vel velit ac, sagittis congue erat. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Suspendisse potenti. Sed egestas, tortor a congue tempus, nisi metus commodo diam, in aliquam libero est non turpis. Mauris diam leo, aliquet eget volutpat vel, feugiat et arcu. Phasellus hendrerit ipsum non tincidunt laoreet. Nulla facilisi. Proin eu ultricies diam, a feugiat lacus.
    `,
    label: ' Curabitur tortor',
    colorClass: s.colorYellow,
  },
  {
    id: 'class_4',
    content: `
      Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Donec varius libero vitae erat facilisis, a viverra elit gravida. Fusce sed tempor metus. Nunc vulputate viverra sem sed fringilla. Etiam libero ante, eleifend non lobortis at, fermentum eu libero. Vivamus ipsum lectus, blandit in quam ut, dignissim tincidunt felis. Mauris semper feugiat sagittis. Sed dui ante, elementum eget nisi in, convallis tempor orci. Praesent imperdiet nec ipsum sit amet tincidunt. Sed bibendum nunc vitae sem ultricies convallis. Nulla justo libero, efficitur sed aliquam in, malesuada in ex. Mauris mattis, lacus et aliquam ultrices, enim leo consectetur ipsum, sed molestie lectus nibh sed neque. Phasellus auctor dui vitae gravida ultricies.
    `,
    label: 'Class aptent',
    colorClass: s.colorRed,
  },
  {
    id: 'nullam_5',
    content: `
      Nullam nulla elit, dapibus ac pulvinar ac, pulvinar a urna. Mauris dapibus mauris nec dignissim sagittis. Fusce consectetur dapibus dui vitae ultricies. Sed egestas imperdiet nisi. Sed iaculis, turpis nec tempor rhoncus, enim elit dapibus leo, eu euismod magna nisl in metus. Proin cursus sollicitudin orci non bibendum. Vivamus mollis lorem turpis, at laoreet ex vulputate sit amet. Nulla nec sapien ultrices, vehicula justo eu, efficitur lacus. Nam in urna convallis, mollis leo consequat, mollis justo. Quisque sit amet eleifend mi. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae; Aenean dictum sit amet ipsum non luctus. Vestibulum efficitur, dui ut scelerisque finibus, est est viverra nunc, vitae varius odio quam ut dolor. Vestibulum at ipsum eget mauris ornare finibus. Curabitur non maximus lacus.
      Nullam ornare nisl quis pharetra commodo. Duis vel tortor nec justo bibendum cursus. Aliquam cursus semper egestas. Cras consequat aliquet nulla vitae hendrerit. Duis ipsum ante, pulvinar et consequat ac, rhoncus quis ex. Aenean tincidunt sit amet justo vitae dictum. Suspendisse potenti. Donec pulvinar nulla et ipsum rhoncus, ac suscipit diam iaculis. Aliquam non iaculis turpis. Pellentesque porttitor, est sit amet facilisis aliquam, leo neque porttitor nibh, eu vestibulum lacus neque malesuada odio. Donec non pretium velit. Duis sit amet mauris ac metus gravida facilisis. Morbi non felis tempus, lacinia diam consequat, placerat massa. Sed vestibulum nec nisi vel sodales. Aenean placerat eros ac velit ultrices, ac euismod sem aliquet.
      Phasellus pretium mi justo, eu dictum risus tempor ac. Vivamus nec sapien sed sapien lobortis placerat id fringilla lorem. Morbi sollicitudin dolor ac blandit vehicula. Duis consectetur cursus enim vulputate auctor. Cras gravida felis eu porttitor viverra. Aenean varius imperdiet erat a facilisis. Pellentesque egestas lacus a elit vehicula, vitae accumsan orci tincidunt. Suspendisse faucibus auctor ultricies. Nulla orci metus, consectetur non tempus vitae, pretium nec lectus. Vivamus sit amet velit non elit pharetra laoreet. Sed efficitur volutpat mauris, et porttitor nisl facilisis nec. Ut quam mauris, lacinia volutpat ultrices sed, lacinia at justo. Praesent nec neque sit amet tortor tincidunt rutrum eu a elit.
    `,
    label: 'Nullam nulla elit',
  },
];

type Story = StoryObj<typeof AnchorBar>;
export default {
  title: 'uikit/AnchorBar',
  component: AnchorBar,
  argTypes: {},
} as Meta<typeof AnchorBar>;

export const PageWithAnchorBar: Story = {
  render: () => {
    return <PageWithAnchorBarExample />;
  },
};

const PageWithAnchorBarExample = () => {
  return (
    <div className={s.articlesPage}>
      <div>
        {testItemsGroups.map((item) => (
          <div key={item.id} id={item.id} className={s.article}>
            <h2 className={item.colorClass || ''}>{item.label}</h2>
            <p>{item.content}</p>
          </div>
        ))}
      </div>
      <AnchorBar>
        <AnchorList
          items={testItemsGroups.map(({ id, label, colorClass }) => ({ id, label, activeColorClass: colorClass }))}
        />
      </AnchorBar>
    </div>
  );
};
