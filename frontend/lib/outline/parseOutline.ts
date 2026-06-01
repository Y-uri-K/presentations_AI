export type PlanSlide = {
  title: string;
  bullets: string[];
};

const TITLE_TAG_RE = /<TITLE>\s*[\s\S]*?\s*<\/TITLE>/gi;

/** Убирает название презентации — в плане только темы слайдов (#). */
export function stripTitleTag(markdown: string): string {
  return markdown.replace(TITLE_TAG_RE, "").trim();
}

export function extractPresentationTitle(
  markdown: string,
  fallback = "Презентация",
): string {
  const match = markdown.match(/<TITLE>\s*([\s\S]*?)\s*<\/TITLE>/i);
  if (match?.[1]?.trim()) {
    return match[1].trim().slice(0, 120);
  }
  const heading = markdown.match(/^#{1,2}\s+(.+)$/m);
  if (heading?.[1]?.trim()) {
    return heading[1].trim().slice(0, 120);
  }
  return fallback;
}

export function parseOutline(markdown: string): PlanSlide[] {
  const trimmed = stripTitleTag(markdown);
  if (!trimmed) {
    return [];
  }

  const blocks = trimmed.split(/\n(?=#{1,2}\s)/);
  const slides: PlanSlide[] = [];

  for (const block of blocks) {
    const lines = block
      .split("\n")
      .map((line) => line.trimEnd())
      .filter((line) => line.trim().length > 0);
    if (lines.length === 0) {
      continue;
    }

    let title = "";
    const bullets: string[] = [];

    for (const line of lines) {
      const heading = line.match(/^#{1,2}\s+(.+)/);
      if (heading) {
        title = heading[1].trim();
        continue;
      }
      const bullet = line.match(/^(?:[-*•]|\d+[.)])\s+(.+)/);
      if (bullet) {
        bullets.push(bullet[1].trim());
        continue;
      }
      if (!title) {
        title = line.trim();
      } else {
        bullets.push(line.trim());
      }
    }

    if (title || bullets.length > 0) {
      slides.push({ title: title || "Слайд", bullets });
    }
  }

  if (slides.length === 0) {
    return [{ title: "Презентация", bullets: trimmed.split("\n").map((line) => line.trim()).filter(Boolean) }];
  }

  return slides;
}

export function outlineTitleFromMarkdown(markdown: string): string {
  return extractPresentationTitle(markdown);
}
