const isDev = import.meta.env.MODE === "development";

function format(scope: string, message: string): string {
  return `[${scope}] ${message}`;
}

export const logger = {
  info(scope: string, message: string): void {
    if (isDev) {
      console.log(format(scope, message));
    }
  },
  warn(scope: string, message: string): void {
    console.warn(format(scope, message));
  },
  error(scope: string, message: string, err?: unknown): void {
    console.error(format(scope, message), err ?? "");
  },
};
