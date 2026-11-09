import { useCallback } from 'react';
import cn from 'classnames';
import VirtualList from '@uikit/VirtualList/VirtualList';
import {
  DEFAULT_SELECT_MAX_HEIGHT,
  SELECT_ITEM_ESTIMATE_SIZE,
  SELECT_VIRTUAL_LIST_MIN_WIDTH,
  VIRTUALIZE_LIST_MIN_COUNT,
} from '@uikit/Select/Select.constants';
import s from '../InputWithAutocomplete.module.scss';

export interface SuggestionsListProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  isVirtualized?: boolean;
  maxHeight?: number;
  className?: string;
}

export const SuggestionsList = ({
  suggestions,
  onSelect,
  isVirtualized = false,
  maxHeight = DEFAULT_SELECT_MAX_HEIGHT,
  className,
}: SuggestionsListProps) => {
  const handleSelect = useCallback(
    (suggestion: string) => (event: React.MouseEvent) => {
      event.preventDefault();
      onSelect(suggestion);
    },
    [onSelect],
  );

  if (isVirtualized && suggestions.length > VIRTUALIZE_LIST_MIN_COUNT) {
    const listHeight = Math.min(
      maxHeight,
      Math.max(suggestions.length * SELECT_ITEM_ESTIMATE_SIZE, SELECT_ITEM_ESTIMATE_SIZE),
    );

    return (
      <VirtualList
        items={suggestions}
        renderItem={(suggestion) => (
          <div className={s.suggestion} title={suggestion} onMouseDown={handleSelect(suggestion)}>
            {suggestion}
          </div>
        )}
        getItemKey={(suggestion) => suggestion}
        className={cn(s.suggestionsList, s.suggestionsList_virtual, 'scroll', className)}
        style={{ height: listHeight, width: '100%', minWidth: SELECT_VIRTUAL_LIST_MIN_WIDTH }}
        estimateSize={SELECT_ITEM_ESTIMATE_SIZE}
        measureItems={false}
        data-test="suggestions"
      />
    );
  }

  return (
    <ul className={cn(s.suggestionsList, 'scroll', className)} style={{ maxHeight }} data-test="suggestions">
      {suggestions.map((suggestion) => (
        <li key={suggestion} className={s.suggestion} title={suggestion} onMouseDown={handleSelect(suggestion)}>
          {suggestion}
        </li>
      ))}
    </ul>
  );
};
