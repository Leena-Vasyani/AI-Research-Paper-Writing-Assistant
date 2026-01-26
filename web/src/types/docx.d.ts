/* eslint-disable @typescript-eslint/no-explicit-any */
declare module "docx" {
  export class Document {
    constructor(opts?: any);
  }
  export class Paragraph {
    constructor(text?: string | any);
  }
  export const Packer: {
    toBlob(doc: Document): Promise<Blob>;
  };
}
