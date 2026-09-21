export interface StoredTokens { access: string; refresh: string }
export interface TokenStorage {
  read(): Promise<unknown>;
  write(tokens: StoredTokens): Promise<void>;
  remove(): Promise<void>;
}

/** Serialize secure writes and invalidate in-flight results when logout wins. */
export class TokenVault {
  private tokens: StoredTokens | null = null;
  private revision = 0;
  private queue: Promise<unknown> = Promise.resolve();
  constructor(private readonly storage: TokenStorage) {}

  private run<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.queue.then(operation, operation);
    this.queue = result.catch(() => undefined);
    return result;
  }

  async initialize(): Promise<void> {
    const ticket = this.revision;
    await this.run(async () => {
      const value = await this.storage.read();
      if (value === null) return;
      if (typeof value !== "object" || !value ||
          !("access" in value) || typeof value.access !== "string" || !value.access ||
          !("refresh" in value) || typeof value.refresh !== "string" || !value.refresh) {
        await this.storage.remove();
        return;
      }
      if (ticket === this.revision) this.tokens = {access:value.access, refresh:value.refresh};
    });
  }

  get access(): string | null { return this.tokens?.access ?? null; }
  get refresh(): string | null { return this.tokens?.refresh ?? null; }

  async save(tokens: StoredTokens): Promise<void> {
    const ticket = ++this.revision;
    await this.run(async () => {
      try { await this.storage.write(tokens); }
      catch { this.tokens = null; throw new Error("Sesiunea nu a putut fi salvată în siguranță."); }
      if (ticket === this.revision) this.tokens = {...tokens};
    });
  }

  async clear(): Promise<void> {
    ++this.revision;
    this.tokens = null;
    await this.run(() => this.storage.remove());
  }
}
