import React, { useState } from 'react';
import Pagination from '@uikit/Pagination/Pagination';
import { Meta, StoryObj } from '@storybook/react';
import { PaginationProps } from '@uikit/Pagination/Pagination.types';
import { defaultPerPagesList } from '@constants';
import { PaginationParams } from '@uikit/types/list.types';

type Story = StoryObj<typeof Pagination>;

export default {
  title: 'uikit/Pagination',
  component: Pagination,
  argTypes: {
    totalItems: {
      defaultValue: 500,
    },
    pageData: {
      defaultValue: { perPage: 10, pageNumber: 4 } as PaginationParams,
    },
    perPageItems: {
      defaultValue: defaultPerPagesList,
    },
    onChangeData: {
      description: 'Function with PaginationData as incoming params',
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

  const handleOnChange = ({ perPage, pageNumber }: PaginationParams) => {
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
