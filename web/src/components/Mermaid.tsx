"use client";

import React, {
  useEffect,
  useRef,
  useImperativeHandle,
  forwardRef,
} from "react";
import mermaid from "mermaid";

mermaid.initialize({
  startOnLoad: true,
  theme: "dark",
  securityLevel: "loose",
  fontFamily: "inherit",
});

interface MermaidProps {
  chart: string;
}

export interface MermaidRef {
  downloadSVG: () => void;
  downloadPNG: () => void;
}

const Mermaid = forwardRef<MermaidRef, MermaidProps>(
  ({ chart }, forwardedRef) => {
    const ref = useRef<HTMLDivElement>(null);

    useImperativeHandle(forwardedRef, () => ({
      downloadSVG: () => {
        if (!ref.current) return;
        const svg = ref.current.querySelector("svg");
        if (!svg) return;

        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], { type: "image/svg+xml" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `diagram-${Date.now()}.svg`;
        link.click();
        URL.revokeObjectURL(url);
      },
      downloadPNG: () => {
        if (!ref.current) return;
        const svg = ref.current.querySelector("svg");
        if (!svg) return;

        // Clone the SVG to avoid modifying the original
        const clonedSvg = svg.cloneNode(true) as SVGElement;

        // Get SVG dimensions
        const bbox = svg.getBBox();
        const width = bbox.width || 800;
        const height = bbox.height || 600;

        // Set explicit dimensions on cloned SVG
        clonedSvg.setAttribute("width", String(width));
        clonedSvg.setAttribute("height", String(height));

        const svgData = new XMLSerializer().serializeToString(clonedSvg);
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        // Set canvas size with scale for better quality
        const scale = 2;
        canvas.width = width * scale;
        canvas.height = height * scale;

        const img = new Image();

        // Use data URL instead of blob URL to avoid CORS issues
        const svgBase64 = btoa(unescape(encodeURIComponent(svgData)));
        const dataUrl = `data:image/svg+xml;base64,${svgBase64}`;

        img.onload = () => {
          if (ctx) {
            ctx.scale(scale, scale);
            ctx.drawImage(img, 0, 0);

            canvas.toBlob((blob) => {
              if (blob) {
                const pngUrl = URL.createObjectURL(blob);
                const link = document.createElement("a");
                link.href = pngUrl;
                link.download = `diagram-${Date.now()}.png`;
                link.click();
                URL.revokeObjectURL(pngUrl);
              }
            }, "image/png");
          }
        };

        img.onerror = () => {
          console.error("Failed to load SVG for PNG conversion");
        };

        img.src = dataUrl;
      },
    }));

    useEffect(() => {
      if (ref.current && chart) {
        // Clear previous content
        ref.current.innerHTML = "";

        // Generate unique ID for each render
        const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

        try {
          mermaid.render(id, chart).then(({ svg }) => {
            if (ref.current) {
              ref.current.innerHTML = svg;
            }
          });
        } catch (error) {
          console.error("Mermaid parsing error:", error);
          if (ref.current) {
            ref.current.innerHTML = `<div class="p-4 text-red-400 bg-red-900/20 rounded-lg">
            Syntax error in diagram definition.
          </div>`;
          }
        }
      }
    }, [chart]);

    return (
      <div
        ref={ref}
        className="flex justify-center overflow-auto rounded-xl bg-zinc-950/40 p-4"
      />
    );
  },
);

Mermaid.displayName = "Mermaid";

export default Mermaid;
