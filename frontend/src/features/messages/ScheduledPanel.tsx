import { type FormEvent, useEffect, useState } from "react";
import { CalendarClock, Pencil, Trash2, X } from "lucide-react";

import { messagesApi } from "../../api/endpoints";
import type { Message } from "../../api/types";
import {
  Button,
  EmptyState,
  ErrorNotice,
  Field,
  IconButton,
  LoadingState,
  Modal,
} from "../../components/ui";
import { useToast } from "../../components/ToastProvider";
import {
  formatMessageTime,
  toLocalDateTimeInput,
  toUtcISOString,
} from "../../utils/format";

interface ScheduledPanelProps {
  open: boolean;
  onClose: () => void;
}

export function ScheduledPanel({ open, onClose }: ScheduledPanelProps) {
  const { showToast } = useToast();
  const [messages, setMessages] = useState<Message[]>([]);
  const [editing, setEditing] = useState<Message | null>(null);
  const [draft, setDraft] = useState("");
  const [scheduledFor, setScheduledFor] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    setError(null);
    messagesApi
      .scheduled()
      .then((page) => {
        if (active) setMessages(page.results);
      })
      .catch((reason) => {
        if (active) {
          setError(
            reason instanceof Error
              ? reason.message
              : "Could not load scheduled messages.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [open]);

  function beginEdit(message: Message) {
    setEditing(message);
    setDraft(message.text);
    setScheduledFor(
      message.scheduled_for
        ? toLocalDateTimeInput(message.scheduled_for)
        : "",
    );
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!editing || !scheduledFor) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await messagesApi.updateScheduled(editing.id, {
        text: draft.trim(),
        scheduled_for: toUtcISOString(scheduledFor),
      });
      setMessages((current) =>
        current.map((message) => (message.id === updated.id ? updated : message)),
      );
      setEditing(null);
      showToast("Scheduled message updated.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update.");
    } finally {
      setSaving(false);
    }
  }

  async function cancel(message: Message) {
    if (!window.confirm("Cancel this scheduled message?")) return;
    try {
      await messagesApi.cancelScheduled(message.id);
      setMessages((current) =>
        current.filter((item) => item.id !== message.id),
      );
      showToast("Scheduled message cancelled.", "success");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not cancel.");
    }
  }

  if (!open) return null;

  return (
    <>
      <aside className="side-panel" aria-label="Scheduled messages">
        <header className="side-panel__header">
          <div>
            <span className="eyebrow">Pending delivery</span>
            <h2>Scheduled messages</h2>
          </div>
          <IconButton label="Close scheduled messages" onClick={onClose}>
            <X size={18} />
          </IconButton>
        </header>
        <div className="side-panel__content">
          {error ? <ErrorNotice message={error} /> : null}
          {loading ? <LoadingState label="Loading scheduled messages" /> : null}
          {!loading && !messages.length ? (
            <EmptyState
              title="Nothing scheduled"
              description="Use the clock beside the message box to choose a future delivery time."
            />
          ) : (
            <ol className="scheduled-list">
              {messages.map((message) => (
                <li key={message.id}>
                  <span className="scheduled-list__icon">
                    <CalendarClock size={18} />
                  </span>
                  <div>
                    <strong>{message.text || "Attachment message"}</strong>
                    <time dateTime={message.scheduled_for ?? ""}>
                      {formatMessageTime(message.scheduled_for)}
                    </time>
                  </div>
                  <IconButton
                    label="Edit scheduled message"
                    onClick={() => beginEdit(message)}
                  >
                    <Pencil size={15} />
                  </IconButton>
                  <IconButton
                    label="Cancel scheduled message"
                    className="icon-button--danger"
                    onClick={() => cancel(message)}
                  >
                    <Trash2 size={15} />
                  </IconButton>
                </li>
              ))}
            </ol>
          )}
        </div>
      </aside>

      <Modal
        open={Boolean(editing)}
        onClose={() => setEditing(null)}
        title="Edit scheduled message"
        width="small"
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button type="submit" form="edit-scheduled" busy={saving}>
              Save changes
            </Button>
          </>
        }
      >
        <form id="edit-scheduled" className="stack" onSubmit={save}>
          <Field label="Message">
            <textarea
              rows={4}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              required={!editing?.attachments.length}
            />
          </Field>
          <Field label="Send date and time">
            <input
              type="datetime-local"
              value={scheduledFor}
              min={toLocalDateTimeInput(new Date(Date.now() + 60_000).toISOString())}
              onChange={(event) => setScheduledFor(event.target.value)}
              required
            />
          </Field>
        </form>
      </Modal>
    </>
  );
}
