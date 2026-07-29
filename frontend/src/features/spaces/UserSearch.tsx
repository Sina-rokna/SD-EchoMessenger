import { useEffect, useId, useState } from "react";
import { LoaderCircle, Search, UserPlus, X } from "lucide-react";

import { usersApi } from "../../api/endpoints";
import type { User } from "../../api/types";
import { Avatar, IconButton } from "../../components/ui";

interface UserSearchProps {
  selected: User[];
  onChange: (users: User[]) => void;
  excludeIds?: string[];
  single?: boolean;
  label?: string;
}

export function UserSearch({
  selected,
  onChange,
  excludeIds = [],
  single = false,
  label = "Find people",
}: UserSearchProps) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const blockedIdsKey = [...excludeIds, ...selected.map((user) => user.id)]
    .sort()
    .join(",");

  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setError(null);
      return;
    }

    let active = true;
    const timer = window.setTimeout(() => {
      setLoading(true);
      usersApi
        .search(trimmed)
        .then((page) => {
          if (!active) return;
          const blocked = new Set(blockedIdsKey.split(",").filter(Boolean));
          setResults(page.results.filter((user) => !blocked.has(user.id)));
          setError(null);
        })
        .catch((reason) => {
          if (active) {
            setError(
              reason instanceof Error ? reason.message : "Search failed.",
            );
          }
        })
        .finally(() => {
          if (active) setLoading(false);
        });
    }, 300);

    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [blockedIdsKey, query]);

  function selectUser(user: User) {
    onChange(single ? [user] : [...selected, user]);
    setQuery("");
    setResults([]);
  }

  return (
    <div className="user-search">
      <label className="field__label" htmlFor={`${listId}-input`}>
        {label}
      </label>
      {selected.length ? (
        <div className="user-search__selected" aria-label="Selected people">
          {selected.map((user) => (
            <span className="person-chip" key={user.id}>
              <Avatar user={user} size="small" />
              {user.username}
              <IconButton
                label={`Remove ${user.username}`}
                onClick={() =>
                  onChange(selected.filter((item) => item.id !== user.id))
                }
              >
                <X size={13} />
              </IconButton>
            </span>
          ))}
        </div>
      ) : null}
      <div className="search-input">
        <Search size={17} aria-hidden />
        <input
          id={`${listId}-input`}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by username or email"
          role="combobox"
          aria-expanded={results.length > 0}
          aria-controls={listId}
          autoComplete="off"
        />
        {loading ? <LoaderCircle className="spin" size={16} aria-label="Searching" /> : null}
      </div>
      {error ? <span className="field__error">{error}</span> : null}
      {query.trim().length >= 2 && !loading ? (
        <div className="user-search__results" id={listId} role="listbox">
          {results.length ? (
            results.map((user) => (
              <button
                type="button"
                role="option"
                aria-selected="false"
                key={user.id}
                onClick={() => selectUser(user)}
              >
                <Avatar user={user} size="small" />
                <span>
                  <strong>{user.username}</strong>
                  {user.email ? <small>{user.email}</small> : null}
                </span>
                <UserPlus size={16} aria-hidden />
              </button>
            ))
          ) : (
            <p>No matching people found.</p>
          )}
        </div>
      ) : null}
    </div>
  );
}
