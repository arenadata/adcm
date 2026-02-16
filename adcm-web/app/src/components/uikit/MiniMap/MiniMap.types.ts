export interface MiniMapConfigProps {
  contentTopOffset: number;
  caretHeight: number;
  caretTopOffset: number;
  wrapperMaxScroll: number;
}

export interface GetHeightProps {
  contentWrapper: HTMLDivElement;
  scrollWrapper: HTMLDivElement;
  minimapContentHeight: number;
  minimapTopOffset: number;
  buttonOffset: number;
}
