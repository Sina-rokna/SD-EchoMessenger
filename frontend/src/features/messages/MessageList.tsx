import { type FormEvent, useEffect, useRef, useState } from "react";
import {
  Download,
  File,
  Image as ImageIcon,
  Pencil,
  Trash2,
} from "lucide-react";

import type { Attachment, Message, PermissionSet } from "../../api/types";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorNotice,
  IconButton,
  LoadingState,
} from "../../components/ui";
import { formatFileSize, formatMessageTime } from "../../utils/format";

interface MessageListProps {
  messages: Message[];
  currentUserId: string;
  permissions: PermissionSet;
  loading: boolean;
  loadingOlder?: boolean;
  error: string | null;
  hasOlder: boolean;
  onLoadOlder: () => void;
  onEdit: (messageId: string, text: string) => Promise<void>;
  onDelete: (messageId: string) => Promise<void>;
  onOpenProfile: (userId: string) => void;
}

function attachmentUrl(attachment: Attachment): string {
  return (
    attachment.download_url ??
    `/api/v1/attachments/${attachment.id}/download/`
  );
}

function AttachmentCard({ attachment }: { attachment: Attachment }) {
  const url = attachmentUrl(attachment);

  if (attachment.category === "IMAGE") {
    return (
      <a
        className="attachment attachment--image"
        href={url}
        target="_blank"
        rel="noreferrer"
      >
        <img src={url} alt={attachment.original_name} loading="lazy" />
        <span>
          <ImageIcon size={14} aria-hidden />
          {attachment.original_name}
        </span>
      </a>
    );
  }

  if (attachment.category === "VIDEO") {
    return (
      <div className="attachment attachment--media">
        <video controls preload="metadata">
          <source src={url} type={attachment.content_type} />
        </video>
        <AttachmentCaption attachment={attachment} />
      </div>
    );
  }

  if (attachment.category === "AUDIO") {
    return (
      <div className="attachment attachment--audio">
        <audio controls preload="metadata">
          <source src={url} type={attachment.content_type} />
        </audio>
        <AttachmentCaption attachment={attachment} />
      </div>
    );
  }

  return (
    <a className="attachment attachment--file" href={url} download>
      <span className="attachment__icon">
        <File size={19} aria-hidden />
      </span>
      <span>
        <strong>{attachment.original_name}</strong>
        <small>{formatFileSize(attachment.size)}</small>
      </span>
      <Download size={17} aria-hidden />
    </a>
  );
}

function AttachmentCaption({ attachment }: { attachment: Attachment }) {
  return (
    <a className="attachment__caption" href={attachmentUrl(attachment)} download>
      <span>
        <strong>{attachment.original_name}</strong>
        <small>{formatFileSize(attachment.size)}</small>
      </span>
      <Download size={16} aria-label="Download attachment" />
    </a>
  );
}

export function MessageList({
  messages,
  currentUserId,
  permissions,
  loading,
  loadingOlder,
  error,
  hasOlder,
  onLoadOlder,
  onEdit,
  onDelete,
  onOpenProfile,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const previousLastId = useRef<string | undefined>(undefined);

  useEffect(() => {
    const lastId = messages.at(-1)?.id;
    if (lastId && lastId !== previousLastId.current) {
      bottomRef.current?.scrollIntoView({ block: "end" });
    }
    previousLastId.current = lastId;
  }, [messages]);

  if (loading) return <LoadingState label="Loading messages" />;
  if (error) return <ErrorNotice message={error} />;

  return (
    <div className="message-scroller" aria-live="polite">
      {hasOlder ? (
        <div className="load-older">
          <Button
            variant="ghost"
            busy={loadingOlder}
            onClick={onLoadOlder}
          >
            Load earlier messages
          </Button>
        </div>
      ) : null}

      {!messages.length ? (
        <EmptyState
          title="Start the conversation"
          description="There are no messages here yet. Say hello when you are ready."
        />
      ) : (
        <ol className="message-list" aria-label="Messages">
          {messages.map((message) => {
            const ownsMessage = message.sender.id === currentUserId;
            const canEdit = ownsMessage;
            const canDelete =
              ownsMessage || permissions.can_delete_messages;

            return (
              <MessageItem
                key={message.id}
                message={message}
                canEdit={canEdit}
                canDelete={canDelete}
                onEdit={onEdit}
                onDelete={onDelete}
                onOpenProfile={onOpenProfile}
              />
            );
          })}
        </ol>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function MessageItem({
  message,
  canEdit,
  canDelete,
  onEdit,
  onDelete,
  onOpenProfile,
}: {
  message: Message;
  canEdit: boolean;
  canDelete: boolean;
  onEdit: (messageId: string, text: string) => Promise<void>;
  onDelete: (messageId: string) => Promise<void>;
  onOpenProfile: (userId: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(message.text);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setDraft(message.text), [message.text]);

  async function submitEdit(event: FormEvent) {
    event.preventDefault();
    const nextText = draft.trim();
    if (nextText === message.text) {
      setEditing(false);
      return;
    }
    if (!nextText && !message.attachments.length) {
      setError("A message needs text or at least one attachment.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onEdit(message.id, nextText);
      setEditing(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not edit.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete this message? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      await onDelete(message.id);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete.");
      setBusy(false);
    }
  }

  return (
    <li className="message" data-message-id={message.id}>
      <button
        className="message__avatar"
        onClick={() => onOpenProfile(message.sender.id)}
        aria-label={`View ${message.sender.username}'s profile`}
      >
        <Avatar user={message.sender} />
      </button>
      <article className="message__body">
        <header>
          <button onClick={() => onOpenProfile(message.sender.id)}>
            {message.sender.username}
          </button>
          <time
            dateTime={
              message.sent_at ?? message.created_at ?? message.scheduled_for ?? ""
            }
          >
            {formatMessageTime(
              message.sent_at ?? message.created_at ?? message.scheduled_for,
            )}
          </time>
          {message.edited_at ? <span>(edited)</span> : null}
        </header>

        {editing ? (
          <form className="message-edit" onSubmit={submitEdit}>
            <textarea
              rows={2}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              aria-label="Edit message"
              autoFocus
            />
            <div>
              <Button
                type="button"
                variant="ghost"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
              <Button type="submit" busy={busy}>
                Save
              </Button>
            </div>
          </form>
        ) : message.text ? (
          <p className="message__content">{message.text}</p>
        ) : null}

        {message.attachments.length ? (
          <div className="attachments">
            {message.attachments.map((attachment) => (
              <AttachmentCard attachment={attachment} key={attachment.id} />
            ))}
          </div>
        ) : null}
        {error ? <span className="message__error">{error}</span> : null}
      </article>

      {(canEdit || canDelete) && !editing ? (
        <div className="message__actions">
          {canEdit && message.text ? (
            <IconButton
              label="Edit message"
              onClick={() => setEditing(true)}
              disabled={busy}
            >
              <Pencil size={15} />
            </IconButton>
          ) : null}
          {canDelete ? (
            <IconButton
              label="Delete message"
              className="icon-button--danger"
              onClick={remove}
              disabled={busy}
            >
              <Trash2 size={15} />
            </IconButton>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}
