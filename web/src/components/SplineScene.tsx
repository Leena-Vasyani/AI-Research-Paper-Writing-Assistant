"use client";

import { Component, type ReactNode } from "react";
import dynamic from "next/dynamic";

const Spline = dynamic(() => import("@splinetool/react-spline"), {
  ssr: false,
});

const defaultPublicUrl =
  "https://my.spline.design/interactivepapercopycopy-JdVwdcQ0P0qagiivQeE5WeZY-YsV/";

function normalizeSplineSceneUrl(url: string): string {
  const trimmed = url.trim();

  if (trimmed.endsWith(".splinecode")) {
    return trimmed;
  }

  if (trimmed.startsWith("https://prod.spline.design/")) {
    return `${trimmed.replace(/\/$/, "")}/scene.splinecode`;
  }

  if (trimmed.startsWith("https://my.spline.design/")) {
    try {
      const parsed = new URL(trimmed);
      const slug = parsed.pathname.replace(/^\//, "").replace(/\/$/, "");
      const idMatch = slug.match(/-([A-Za-z0-9]{20,})(?:-[A-Za-z0-9]+)?$/);
      if (idMatch?.[1]) {
        return `https://prod.spline.design/${idMatch[1]}/scene.splinecode`;
      }
    } catch {
      return "";
    }
  }

  return "";
}

function isRuntimeAllowed(sceneUrl: string): boolean {
  const runtimeEnabled = process.env.NEXT_PUBLIC_SPLINE_USE_RUNTIME === "true";
  return (
    runtimeEnabled &&
    sceneUrl.startsWith("https://prod.spline.design/") &&
    sceneUrl.endsWith(".splinecode")
  );
}

class SplineErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean }
> {
  constructor(props: { fallback: ReactNode; children: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  override render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

export default function SplineScene({
  src,
  title,
  className = "",
}: {
  src?: string;
  title: string;
  className?: string;
}) {
  const rawSrc =
    src?.trim() ||
    process.env.NEXT_PUBLIC_SPLINE_SITE_SCENE_URL ||
    process.env.NEXT_PUBLIC_SPLINE_SITE_PREVIEW_URL ||
    process.env.NEXT_PUBLIC_SPLINE_HERO_URL ||
    defaultPublicUrl;

  const sceneSrc = normalizeSplineSceneUrl(rawSrc);
  const useRuntime = sceneSrc ? isRuntimeAllowed(sceneSrc) : false;

  return (
    <div className={`relative overflow-hidden ${className}`}>
      <div className="sr-only">{title}</div>
      {sceneSrc && useRuntime ? (
        <SplineErrorBoundary
          fallback={
            <iframe
              src={rawSrc}
              title={title}
              className="h-full w-full border-0"
              loading="eager"
              allow="fullscreen; xr-spatial-tracking; accelerometer; gyroscope; autoplay"
              referrerPolicy="strict-origin-when-cross-origin"
              scrolling="no"
              allowFullScreen
            />
          }
        >
          <Spline scene={sceneSrc} className="h-full w-full" />
        </SplineErrorBoundary>
      ) : (
        <iframe
          src={rawSrc}
          title={title}
          className="h-full w-full border-0"
          loading="eager"
          allow="fullscreen; xr-spatial-tracking; accelerometer; gyroscope; autoplay"
          referrerPolicy="strict-origin-when-cross-origin"
          scrolling="no"
          allowFullScreen
        />
      )}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-zinc-950 to-transparent" />
    </div>
  );
}
