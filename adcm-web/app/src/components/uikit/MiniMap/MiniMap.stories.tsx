import MiniMap from './MiniMap';
import { useRef } from 'react';
import type { Meta, StoryObj } from '@storybook/react';
import s from '@uikit/MiniMap/MiniMap.stories.module.scss';
import cn from 'classnames';

type Story = StoryObj<typeof MiniMap>;
export default {
  title: 'uikit/MiniMap',
  component: MiniMap,
  argTypes: {},
} as Meta<typeof MiniMap>;

const MiniMapExampleComponent = () => {
  const scrollableWrapperRef = useRef<HTMLDivElement>(null);
  const contentWrapperRef = useRef<HTMLDivElement>(null);
  const groupOfBlockCount = [...new Array(10)].map(() => Math.random() * 1000);

  return (
    <div className={s.wrapperWithScroll} ref={scrollableWrapperRef}>
      <div className={s.pageHeader}>Like a header</div>
      <MiniMap contentWrapperRef={contentWrapperRef} scrollableWrapperRef={scrollableWrapperRef}>
        <div className={s.contentWrapper} ref={contentWrapperRef}>
          {groupOfBlockCount.map((key, id) => {
            return (
              <div key={`someKey ${key}`}>
                <div className={cn(s.colorfulBlock, s.colorfulBlock_green, s.shortBlock)}>
                  <h1>Some huge header to see where we are {id}</h1>
                </div>
                <div className={cn(s.colorfulBlock, s.colorfulBlock_lightgrey, s.wideBlock)}>
                  ___________________________________________________________________
                </div>
                <div className={cn(s.colorfulBlock, s.colorfulBlock_grey, s.wideBlock)}>
                  Another text! This text is long! Text as long as i could write some long text to show how minimap cut
                  the very long parts of minimaped component and there is a lot of
                  ___________________________________________________________________ because you will definitely see
                  them on minimap if they in block
                </div>
              </div>
            );
          })}
        </div>
      </MiniMap>
    </div>
  );
};

export const MiniMapExample: Story = {
  render: () => {
    return <MiniMapExampleComponent />;
  },
};
