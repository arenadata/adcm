import React, { PropsWithChildren, RefObject, useRef } from 'react';
import { Meta, StoryObj } from '@storybook/react';
import ScrollBar from '@uikit/ScrollBar/ScrollBar';
import ScrollBarWrapper from '@uikit/ScrollBar/ScrollBarWrapper';
import s from './ScrollBarStories.module.scss';
import { Text } from '@uikit';

type Story = StoryObj<typeof ScrollBar>;

export default {
  title: 'uikit/ScrollBar',
  component: ScrollBar,
  argTypes: {
    variant: {
      defaultValue: 'vertical',
    },
  },
} as Meta<typeof ScrollBar>;

export const ScrollBarStory: Story = {
  render: () => <ScrollBarExample />,
};

interface TextContentProps extends PropsWithChildren {
  contentRef: RefObject<HTMLDivElement>;
}

const TextContent = ({ contentRef, children }: TextContentProps) => {
  return (
    <div className={s.contentWrapper} ref={contentRef}>
      <Text variant="h1">Chicken Coder: the incredible coder journey!</Text>
      <p>
        Once upon a time, in the bustling town of Techtopia, there lived a peculiar chicken named Cluckbert. Unlike the
        other chickens in the coop, Cluckbert was not content with the simple life of pecking at grains and strutting
        around the yard. No, Cluckbert had grand dreams of becoming a coder.
      </p>
      <p>
        Every day, while the other chickens were busy with their usual activities, Cluckbert would perch himself on a
        pile of hay in the corner of the coop, pecking away at an old keyboard he had found discarded in the barn. He
        had a natural talent for understanding patterns and logic, and soon he began to experiment with simple lines of
        code.
      </p>
      <p>
        His fellow chickens thought Cluckbert was simply scratching at the keys for fun, but little did they know that
        he was actually teaching himself the basics of programming. He studied online tutorials, read coding books
        scavenged from the farmer's library, and even attended virtual coding classes whenever he could find them.
      </p>
      <p>
        As days turned into weeks and weeks into months, Cluckbert's coding skills grew by leaps and bounds. He wrote
        programs to help the farmer keep track of egg production, algorithms to optimize the feeding schedule for the
        chickens, and even games to entertain his fellow coop-mates during their downtime.
      </p>
      <p>
        But Cluckbert's ambitions didn't stop there. He dreamed of creating something truly groundbreaking, something
        that would change the world of technology forever. And so, with determination in his heart and a gleam in his
        eye, Cluckbert set out to develop his masterpiece: an app that would revolutionize the way chickens communicated
        with each other.
      </p>
      <p>
        Day and night, Cluckbert tirelessly worked on his project, pecking away at the keyboard with unwavering focus.
        He encountered countless bugs and setbacks along the way, but he refused to give up. With each obstacle he
        overcame, Cluckbert grew more determined to see his vision come to life.
      </p>
      <p>
        Finally, after months of hard work, Cluckbert unveiled his app to the world: "ChickChat." It was a messaging
        platform designed specifically for chickens, complete with customizable emojis and built-in translation features
        for different dialects. The response from the chicken community was overwhelmingly positive, and soon ChickChat
        became the talk of the town.
      </p>
      <p>
        News of Cluckbert's remarkable achievement spread far and wide, attracting attention from tech enthusiasts and
        poultry aficionados alike. Before long, he was invited to speak at coding conferences and innovation summits,
        where he shared his story with audiences of humans and chickens alike.
      </p>
      <p>
        But amidst all the fame and recognition, Cluckbert remained humble and grounded. He never forgot his roots or
        the coop-mates who had supported him from the beginning. And though he had achieved his dream of becoming a
        coder, Cluckbert knew that his journey was far from over.
      </p>
      <p>
        For Cluckbert, the sky was the limit, and he couldn't wait to see where his coding adventures would take him
        next. And so, with a contented cluck and a satisfied smile, he returned to his keyboard, ready to tackle
        whatever challenges lay ahead. After all, for a chicken with a passion for coding, the world was full of endless
        possibilities.
      </p>

      <Text variant="h1">Unchecked Lines: The Story of Matilda's Code Catastrophe</Text>
      <p>
        Once upon a time, in the bustling world of tech, there was a small but talented mouse named Matilda who worked
        as a software engineer in a vibrant company called ByteTech Inc. Matilda was known for her exceptional coding
        skills and her ability to churn out lines of code with lightning speed. However, there was one aspect of her job
        that Matilda consistently neglected: code reviews.
      </p>
      <p>
        While her colleagues diligently reviewed each other's code, offering valuable feedback and catching potential
        bugs before they became serious issues, Matilda preferred to work in isolation. She believed that her code was
        flawless and didn't need the scrutiny of others. "Why waste time reviewing code when I can just get the job done
        myself?" she would often muse, brushing off her colleagues' suggestions to participate in the review process.
      </p>
      <p>
        At first, Matilda's approach seemed to work. Her projects were completed on time, and her code appeared to
        function smoothly. However, as time went on, cracks began to appear in Matilda's flawless facade.
      </p>
      <p>
        One day, the company launched a new software update that Matilda had been working on for weeks. Excited to see
        her hard work come to fruition, Matilda eagerly clicked the "update" button, expecting smooth sailing ahead.
      </p>
      <p>
        But as soon as the update went live, disaster struck. Users reported a myriad of issues ranging from glitches
        and crashes to security vulnerabilities. Panic swept through ByteTech Inc. as the company scrambled to address
        the fallout from the faulty update.
      </p>
      <p>
        As the chaos unfolded around her, Matilda found herself in hot water. It quickly became apparent that the root
        cause of the problems stemmed from her code, which had not undergone proper review and testing. Without the
        fresh eyes of her colleagues to catch potential flaws, critical bugs had slipped through the cracks and wreaked
        havoc on the company's software. Feeling a sinking sense of guilt and regret, Matilda realized the gravity of
        her mistake. By neglecting to participate in code reviews, she had not only let down her colleagues but also
        jeopardized the reputation of the entire company.
      </p>
      <p>
        In the aftermath of the debacle, Matilda faced the consequences of her actions. She was reprimanded by her
        superiors and tasked with the arduous process of identifying and fixing the issues in her code. It was a
        humbling experience for Matilda, who came to understand the importance of collaboration and peer review in the
        world of software development.
      </p>
      <p>
        From that day forward, Matilda made a vow to always prioritize code reviews and to actively seek feedback from
        her colleagues. Though the lesson had been learned the hard way, Matilda emerged from the experience as a wiser
        and more conscientious engineer, determined never to repeat her past mistakes. And as she worked alongside her
        fellow mice at ByteTech Inc., she knew that together, they could overcome any challenge that came their way.
      </p>
      {children}
    </div>
  );
};

const ScrollBarExample = () => {
  const contentRef = useRef<HTMLDivElement>(null);
  const contentRefSecond = useRef<HTMLDivElement>(null);

  return (
    <>
      <Text variant="h1">Default scrollbar</Text>
      <div className={s.allMightyWrapper}>
        <ScrollBarWrapper position="right">
          <ScrollBar contentRef={contentRef} orientation="vertical" />
        </ScrollBarWrapper>
        <ScrollBarWrapper position="bottom">
          <ScrollBar contentRef={contentRef} orientation="horizontal" />
        </ScrollBarWrapper>

        <TextContent contentRef={contentRef}>
          <div className={s.longBlock}>
            <p>
              "Test long text" is a phrase often used to verify the display and formatting of text in various contexts,
              particularly in software development. It's a placeholder for content, allowing developers to assess how
              text appears within a layout or interface before finalizing it with actual content.
            </p>
          </div>
        </TextContent>
      </div>

      <Text variant="h1">Custom scroll bar, with container stretchable by width</Text>
      <div className={s.allMightyWrapper}>
        <div className={s.scrollWrapperLeft}>
          <ScrollBar
            trackClasses={s.scrollWrapperLeft_track}
            contentRef={contentRefSecond}
            thumbClasses={s.thumb}
            orientation="vertical"
          />
        </div>
        <ScrollBarWrapper position="top">
          <ScrollBar
            trackClasses={s.scrollTop}
            thumbClasses={s.thumb}
            contentRef={contentRefSecond}
            orientation="horizontal"
          />
        </ScrollBarWrapper>

        <ScrollBarWrapper position="bottom">
          <ScrollBar
            trackClasses={s.scrollBottom}
            thumbClasses={s.thumb}
            contentRef={contentRefSecond}
            orientation="horizontal"
          />
        </ScrollBarWrapper>

        <TextContent contentRef={contentRefSecond}>
          <div className={s.stretchableBlock}>
            <p>
              "Test long text" is a phrase often used to verify the display and formatting of text in various contexts,
              particularly in software development. It's a placeholder for content, allowing developers to assess how
              text appears within a layout or interface before finalizing it with actual content.
            </p>
          </div>
        </TextContent>
      </div>
    </>
  );
};
