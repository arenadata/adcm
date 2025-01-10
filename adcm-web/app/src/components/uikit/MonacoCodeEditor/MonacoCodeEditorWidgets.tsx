import type { MonacoCodeEditorWidget } from './MonacoCodeEditor.types';

export interface MonacoCodeEditorWidgetsProps {
  widgets?: MonacoCodeEditorWidget[];
}

const MonacoCodeEditorWidgets = ({ widgets }: MonacoCodeEditorWidgetsProps) => {
  return <>{widgets?.map((w) => w.renderWidget())}</>;
};

export default MonacoCodeEditorWidgets;
