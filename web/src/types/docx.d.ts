declare module "docx" {
  export class Document {
    constructor(opts?: Record<string, unknown>);
  }
  export class Paragraph {
    constructor(text?: string | Record<string, unknown>);
  }
  export const Packer: {
    toBlob(doc: Document): Promise<Blob>;
  };
}
