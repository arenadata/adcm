export const mappingUrl = 'http://myserver/mapping.json';

export const mappingText = `mapping: 
  service 1:
    component 1:
      - host 1
  service 2:
    component 2:
      - host 1
`;

export const mappingSchema = {
  uri: 'http://myserver/mapping-schema.json',
  fileMatch: [mappingUrl], // associate with our model
  schema: {
    type: 'object',
    properties: {
      mapping: {
        type: 'object',
      },
    },
  },
};
