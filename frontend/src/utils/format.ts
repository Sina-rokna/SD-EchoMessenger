const relativeFormatter = new Intl.RelativeTimeFormat(undefined, {
  numeric: "auto",
});

export function formatMessageTime(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();

  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    ...(sameDay
      ? {}
      : {
          month: "short",
          day: "numeric",
          year: date.getFullYear() === now.getFullYear() ? undefined : "numeric",
        }),
  }).format(date);
}

export function formatRelativeTime(value: string): string {
  const difference = new Date(value).getTime() - Date.now();
  const absolute = Math.abs(difference);

  if (absolute < 60_000) return "just now";
  if (absolute < 3_600_000) {
    return relativeFormatter.format(Math.round(difference / 60_000), "minute");
  }
  if (absolute < 86_400_000) {
    return relativeFormatter.format(Math.round(difference / 3_600_000), "hour");
  }
  return relativeFormatter.format(Math.round(difference / 86_400_000), "day");
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

export function toLocalDateTimeInput(value: string): string {
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

export function toUtcISOString(localValue: string): string {
  return new Date(localValue).toISOString();
}
