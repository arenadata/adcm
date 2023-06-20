import React, { useState } from 'react';
import Pagination, { PaginationDataProps, defaultPerPagesList, PaginationProps } from '@uikit/Pagination/Pagination';
import { Meta, StoryObj } from '@storybook/react';

type Story = StoryObj<typeof Pagination>;

export default {
  title: 'uikit/Pagination',
  component: Pagination,
  argTypes: {
    totalItems: {
      defaultValue: 500 | undefined,
    },
    pageData: {
      defaultValue: { perPage: 10, pageNumber: 4 } as PaginationDataProps,
    },
    perPageItems: {
      defaultValue: defaultPerPagesList,
    },
    onChangeData: {
      description: 'Function with PaginationDataProps as incoming params',
    },
    isNextBtn: {
      defaultValue: null,
    },
    hidePerPage: {
      defaultValue: false,
    },
  },
} as Meta<typeof Pagination>;

export const Paginations: Story = {
  args: {
    pageData: { perPage: 10, pageNumber: 4 },
    totalItems: 145,
  },

  render: (args) => <PaginationStory {...args} />,
};

const PaginationStory = ({ totalItems, pageData, perPageItems, isNextBtn, hidePerPage }: PaginationProps) => {
  const [curPageData, setCurPageData] = useState(pageData);

  const handleOnChange = ({ perPage, pageNumber }) => {
    setCurPageData({ perPage, pageNumber });
  };

  return (
    <Pagination
      onChangeData={handleOnChange}
      pageData={curPageData}
      totalItems={totalItems}
      perPageItems={perPageItems}
      isNextBtn={isNextBtn}
      hidePerPage={hidePerPage}
    />
  );
};
