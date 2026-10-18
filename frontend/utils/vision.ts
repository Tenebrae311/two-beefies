import type { VisionResult } from "./types";

/** Tools that hand an image to Nemotron 3.5 Super VL instead of searching text. */
export const VISION_TOOLS = new Set(["inspect_page_image", "compare_images"]);
export const VISION_MODEL_LABEL = "Nemotron 3.5 Super VL";

export function isVisionTool(name: string | undefined): boolean {
  return !!name && VISION_TOOLS.has(name);
}

/** Live status text while a tool call is pending. */
export function pendingToolLabel(name: string, eb: boolean): string {
  if (name === "inspect_page_image") return "examining the original page…";
  if (name === "compare_images") return eb ? "comparing the engraving with today’s image…" : "comparing the images…";
  return eb ? "consulting the archives" : "searching";
}

export function visionTitle(name: string): string {
  return name === "compare_images" ? "Compared the old engraving with today’s image" : "Looked at the original scan";
}

/** Which encyclopaedia an image URL belongs to (Britannica scans are served by the backend or /mock/eb-*). */
export function imageSource(url: string): "britannica" | "wikipedia" {
  if (/\/api\/page-image\//.test(url) || /\/mock\/eb-/.test(url)) return "britannica";
  if (/^https?:\/\//i.test(url) || /\/mock\/wp-/.test(url)) return "wikipedia";
  return "britannica";
}

export function normalizeVision(v: Partial<VisionResult> | null | undefined): VisionResult | null {
  if (!v) return null;
  return {
    question: String(v.question ?? ""),
    answer: String(v.answer ?? ""),
    images: Array.isArray(v.images) ? v.images.filter((x) => typeof x === "string" && x) : [],
  };
}
