import type { Meta, StoryFn } from '@storybook/react';
import SyncScroll from './SyncScroll';
import ScrollPane from './ScrollPane';

export default {
  title: 'uikit/SyncScroll',
  component: SyncScroll,
  argTypes: {},
} as Meta<typeof SyncScroll>;

const Template: StoryFn<typeof SyncScroll> = () => {
  return (
    <SyncScroll>
      <ScrollPane>
        <div style={{ width: '500px', height: '300px', border: '1px solid' }}>
          Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras maximus tincidunt est, facilisis tempus odio
          accumsan ac. Etiam fringilla mattis ex vitae commodo. Duis malesuada quis justo id facilisis. In rhoncus
          laoreet neque, eget fermentum purus tempor vel. Vestibulum faucibus magna eget pharetra rhoncus. Aenean
          rhoncus diam eget ex rhoncus, vitae malesuada nulla suscipit. Etiam sem ante, bibendum sit amet purus vitae,
          mattis convallis tellus. Vivamus quis tortor consectetur, consequat sem in, cursus orci. Praesent pretium
          mauris sed odio dignissim feugiat. Sed semper nunc nunc, non volutpat libero dapibus ac. Etiam condimentum
          eros in quam tristique lacinia. Nulla at ultricies risus. Vestibulum non metus lacus. Interdum et malesuada
          fames ac ante ipsum primis in faucibus. Aliquam sed feugiat leo. In ornare iaculis nisl, non facilisis nulla
          efficitur ac. Etiam venenatis imperdiet diam id dapibus. Vivamus hendrerit, odio eget volutpat tincidunt,
          dolor tortor volutpat massa, eu maximus turpis purus eget odio. Praesent augue nunc, dapibus sed ligula id,
          tristique vehicula massa. Donec non blandit sapien. Nullam feugiat vehicula ultricies. Phasellus at tortor at
          est malesuada scelerisque ut et turpis. Praesent id dolor porttitor, dignissim ex non, porta augue. Vestibulum
          vel ultricies ipsum. Quisque non suscipit sapien. Integer commodo a felis id ornare. Duis a eros id elit
          fermentum finibus. Duis ultrices metus augue, vitae dictum eros placerat nec. Donec at nulla sit amet ante
          egestas vehicula nec nec diam. Vivamus pulvinar arcu ante, in tristique leo ultricies et. Nam commodo in quam
          quis lobortis. Proin leo nulla, finibus ac efficitur sollicitudin, eleifend euismod erat. Aenean ullamcorper
          est id pretium rhoncus. Maecenas pretium commodo erat, cursus maximus lorem. Fusce semper eros in metus
          bibendum auctor. Quisque nec justo a purus sodales vehicula ac at nisi. Integer vitae dolor viverra metus
          pharetra egestas. Suspendisse sit amet rutrum sapien, sed aliquet ligula. Nam ultricies fermentum ante, et
          vestibulum risus imperdiet pulvinar. Cras sed malesuada magna, eget mollis sapien. Donec accumsan magna vitae
          sem tempor porttitor. Sed sem lacus, hendrerit sed lorem id, vestibulum lacinia lectus. Praesent eu orci elit.
          Pellentesque dictum rutrum malesuada. Ut ut euismod metus, eget blandit velit. Fusce sit amet erat eget turpis
          dignissim mollis. Phasellus efficitur metus sit amet odio interdum tristique. Quisque ultricies vel dui a
          interdum. Sed maximus pulvinar risus, sit amet scelerisque lorem dapibus in. Fusce turpis arcu, gravida ac
          scelerisque et, porta id risus.
        </div>
      </ScrollPane>

      <ScrollPane>
        <div style={{ width: '500px', height: '300px', border: '1px solid' }}>
          Lorem ipsum dolor sit amet, consectetur adipiscing elit. Cras maximus tincidunt est, facilisis tempus odio
          accumsan ac. Etiam fringilla mattis ex vitae commodo. Duis malesuada quis justo id facilisis. In rhoncus
          laoreet neque, eget fermentum purus tempor vel. Vestibulum faucibus magna eget pharetra rhoncus. Aenean
          rhoncus diam eget ex rhoncus, vitae malesuada nulla suscipit. Etiam sem ante, bibendum sit amet purus vitae,
          mattis convallis tellus. Vivamus quis tortor consectetur, consequat sem in, cursus orci. Praesent pretium
          mauris sed odio dignissim feugiat. Sed semper nunc nunc, non volutpat libero dapibus ac. Etiam condimentum
          eros in quam tristique lacinia. Nulla at ultricies risus. Vestibulum non metus lacus. Interdum et malesuada
          fames ac ante ipsum primis in faucibus. Aliquam sed feugiat leo. In ornare iaculis nisl, non facilisis nulla
          efficitur ac. Etiam venenatis imperdiet diam id dapibus. Vivamus hendrerit, odio eget volutpat tincidunt,
          dolor tortor volutpat massa, eu maximus turpis purus eget odio. Praesent augue nunc, dapibus sed ligula id,
          tristique vehicula massa. Donec non blandit sapien. Nullam feugiat vehicula ultricies. Phasellus at tortor at
          est malesuada scelerisque ut et turpis. Praesent id dolor porttitor, dignissim ex non, porta augue. Vestibulum
          vel ultricies ipsum. Quisque non suscipit sapien. Integer commodo a felis id ornare. Duis a eros id elit
          fermentum finibus. Duis ultrices metus augue, vitae dictum eros placerat nec. Donec at nulla sit amet ante
          egestas vehicula nec nec diam. Vivamus pulvinar arcu ante, in tristique leo ultricies et. Nam commodo in quam
          quis lobortis. Proin leo nulla, finibus ac efficitur sollicitudin, eleifend euismod erat. Aenean ullamcorper
          est id pretium rhoncus. Maecenas pretium commodo erat, cursus maximus lorem. Fusce semper eros in metus
          bibendum auctor. Quisque nec justo a purus sodales vehicula ac at nisi. Integer vitae dolor viverra metus
          pharetra egestas. Suspendisse sit amet rutrum sapien, sed aliquet ligula. Nam ultricies fermentum ante, et
          vestibulum risus imperdiet pulvinar. Cras sed malesuada magna, eget mollis sapien. Donec accumsan magna vitae
          sem tempor porttitor. Sed sem lacus, hendrerit sed lorem id, vestibulum lacinia lectus. Praesent eu orci elit.
          Pellentesque dictum rutrum malesuada. Ut ut euismod metus, eget blandit velit. Fusce sit amet erat eget turpis
          dignissim mollis. Phasellus efficitur metus sit amet odio interdum tristique. Quisque ultricies vel dui a
          interdum. Sed maximus pulvinar risus, sit amet scelerisque lorem dapibus in. Fusce turpis arcu, gravida ac
          scelerisque et, porta id risus.
        </div>
      </ScrollPane>
    </SyncScroll>
  );
};

export const SyncScrollStory = Template.bind({});
SyncScrollStory.args = {};
SyncScrollStory.storyName = 'Default';
