// FILE: frontend/src/data/global.d.ts
// PHOENIX PROTOCOL - PHASE 4: TYPE DECLARATION
// 1. PURPOSE: Declares the dom-to-image-more module to satisfy TypeScript compiler (TS7016).

declare module 'dom-to-image-more' {
    interface Options {
        filter?: (node: Node) => boolean;
        bgcolor?: string;
        width?: number;
        height?: number;
        style?: { [key: string]: string };
        quality?: number;
        imagePlaceholder?: string;
        cacheBust?: boolean;
    }

    function toSvg(node: HTMLElement, options?: Options): Promise<string>;
    function toPng(node: HTMLElement, options?: Options): Promise<string>;
    function toJpeg(node: HTMLElement, options?: Options): Promise<string>;
    function toBlob(node: HTMLElement, options?: Options): Promise<Blob>;
    function toPixelData(node: HTMLElement, options?: Options): Promise<Uint8ClampedArray>;
    
    export default { toPng, toSvg, toJpeg, toBlob, toPixelData };
}