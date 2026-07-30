import { type FormEvent, useEffect, useState } from "react";
import { Search, X } from "lucide-react";

import { messagesApi } from "../../api/endpoints";
import type { Message } from "../../api/types";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorNotice,
  IconButton,
  LoadingState,
} from "../../components/ui";
import { formatMessageTime } from "../../utils/format";

interface SearchPanelProps {
  open: boolean;
  spaceId: string;
  topicId?: string | null;
  onClose: () => void;
  onOpenProfile: (userId: string) => void;
}

export function SearchPanel({
  open,
  spaceId,
  topicId,
  onClose,
  onOpenProfile,
}: SearchPanelProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Message[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults(null);
      setError(null);
    }
  }, [open]);

  async function search(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const page = await messagesApi.search(spaceId, query.trim(), topicId);
      setResults(page.results);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <aside className="side-panel" aria-label="Search messages">
      <header className="side-panel__header">
        <div>
          <span className="eyebrow">Current conversation</span>
          <h2>Search messages</h2>
        </div>
        <IconButton label="Close search" onClick={onClose}>
          <X size={18} />
        </IconButton>
      </header>
      <form className="panel-search" onSubmit={search}>
        <Search size={17} aria-hidden />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Type a keyword"
          aria-label="Search query"
          autoFocus
        />
        <Button type="submit" disabled={!query.trim()} busy={loading}>
          Search
        </Button>
      </form>
      <div className="side-panel__content">
        {error ? <ErrorNotice message={error} /> : null}
        {loading ? <LoadingState label="Searching messages" /> : null}
        {!loading && results?.length === 0 ? (
          <EmptyState
            title="No matching messages"
            description="Try a different word or a shorter phrase."
          />
        ) : null}
        {!loading && results?.length ? (
          <ol className="search-results">
            {results.map((message) => (
              <li key={message.id}>
                <button
                  className="search-results__author"
                  onClick={() => onOpenProfile(message.sender.id)}
                >
                  <Avatar user={message.sender} size="small" />
                  <strong>{message.sender.username}</strong>
                </button>
                <time dateTime={message.sent_at ?? ""}>
                  {formatMessageTime(message.sent_at ?? message.created_at)}
                </time>
                <p>
                  {message.text ||
                    `${message.attachments.length} attachment(s)`}
                </p>
              </li>
            ))}
          </ol>
        ) : null}
        {!loading && results === null ? (
          <EmptyState
            title="Find an earlier message"
            description="Results stay inside this conversation, so private messages remain private."
          />
        ) : null}
      </div>
    </aside>
  );
}
