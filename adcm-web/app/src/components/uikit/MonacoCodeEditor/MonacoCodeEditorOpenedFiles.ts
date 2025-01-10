import type { monaco, EditorFile } from './MonacoCodeEditor.types';

export class MonacoCodeEditorOpenedFiles {
  private globalOpenedFiles: { [uri: string]: EditorFile } = {};

  public add(file: EditorFile) {
    this.globalOpenedFiles[file.uri] = file;
  }

  public remove(uri: monaco.Uri) {
    delete this.globalOpenedFiles[uri.toString()];
  }

  public getSchemas() {
    const schemasToFile: Record<string, string[]> = {}; // key: schemaUri, value: fileUri[]
    // biome-ignore lint/suspicious/noExplicitAny:
    const allSchemasUri = new Map<string, any>(); // key: schemaUri, value: schema as object

    for (const [uri, openedFile] of Object.entries(this.globalOpenedFiles)) {
      if (!openedFile.schema) {
        continue;
      }

      const schemaUri = `${uri}_schema.json`;
      allSchemasUri.set(schemaUri, openedFile.schema);

      if (schemasToFile[schemaUri] === undefined) {
        schemasToFile[schemaUri] = [];
      }
      schemasToFile[schemaUri].push(openedFile.uri);
    }

    const schemas = [];
    for (const [schemaUri, schema] of allSchemasUri) {
      schemas.push({
        uri: schemaUri,
        fileMatch: schemasToFile[schemaUri], // associate with our model
        schema: schema,
      });
    }

    return schemas;
  }
}
