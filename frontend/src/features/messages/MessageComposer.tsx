import {
  type ChangeEvent,
  type DragEvent,
  type FormEvent,
  type KeyboardEvent,
  useRef,
  useState,
} from "react";
import {
  CalendarClock,
  FilePlus2,
  Paperclip,
  Send,
  X,
} from "lucide-react";

import { Button, Field, IconButton, Modal } from "../../components/ui";
import { formatFileSize, toUtcISOString } from "../../utils/format";

const MAX_ATTACHMENTS = 5;
const MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024;

interface MessageComposerProps {
  targetName: string;
  disabledReason?: string;
  allowMedia: boolean;
  sending: boolean;
  onSend: (
    text: string,
    attachments: File[],
    scheduledFor?: string,
  ) => Promise<void>;
}

export function MessageComposer({
  targetName,
  disabledReason,
  allowMedia,
  sending,
  onSend,
}: MessageComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState("");
  const [attachments, setAttachments] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleTime, setScheduleTime] = useState("");
  const [minimumScheduleTime, setMinimumScheduleTime] = useState("");
  const [error, setError] = useState<string | null>(null);

  function openSchedule() {
    const date = new Date(Date.now() + 60_000);
    const offset = date.getTimezoneOffset() * 60_000;
    setMinimumScheduleTime(
      new Date(date.getTime() - offset).toISOString().slice(0, 16),
    );
    setScheduleOpen(true);
  }

  function addFiles(incoming: File[]) {
    setError(null);
    if (!allowMedia) {
      setError("Your role does not allow attachments in this channel.");
      return;
    }
    if (attachments.length + incoming.length > MAX_ATTACHMENTS) {
      setError(`A message can contain at most ${MAX_ATTACHMENTS} attachments.`);
      return;
    }
    const oversized = incoming.find((file) => file.size > MAX_ATTACHMENT_SIZE);
    if (oversized) {
      setError(`${oversized.name} is larger than 10 MiB.`);
      return;
    }
    setAttachments((current) => [...current, ...incoming]);
  }

  function handleFiles(event: ChangeEvent<HTMLInputElement>) {
    addFiles(Array.from(event.target.files ?? []));
    event.target.value = "";
  }

  async function submit(scheduledFor?: string) {
    if (!text.trim() && !attachments.length) {
      setError("Write a message or add at least one attachment.");
      return;
    }

    setError(null);
    try {
      await onSend(text.trim(), attachments, scheduledFor);
      setText("");
      setAttachments([]);
      setScheduleTime("");
      setScheduleOpen(false);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Could not send the message.",
      );
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submit();
  }

  function handleSchedule(event: FormEvent) {
    event.preventDefault();
    if (!scheduleTime || new Date(scheduleTime).getTime() <= Date.now()) {
      setError("Choose a time in the future.");
      return;
    }
    void submit(toUtcISOString(scheduleTime));
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!sending && !disabledReason) void submit();
    }
  }

  function handleDrop(event: DragEvent) {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <>
      <form
        className={`composer ${dragging ? "is-dragging" : ""}`}
        onSubmit={handleSubmit}
        onDragEnter={() => setDragging(true)}
        onDragLeave={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget as Node)) {
            setDragging(false);
          }
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        {attachments.length ? (
          <div className="composer__attachments" aria-label="Attachments">
            {attachments.map((file, index) => (
              <span className="file-chip" key={`${file.name}-${index}`}>
                <FilePlus2 size={15} aria-hidden />
                <span>
                  <strong>{file.name}</strong>
                  <small>{formatFileSize(file.size)}</small>
                </span>
                <IconButton
                  label={`Remove ${file.name}`}
                  onClick={() =>
                    setAttachments((current) =>
                      current.filter((_, fileIndex) => fileIndex !== index),
                    )
                  }
                >
                  <X size={14} />
                </IconButton>
              </span>
            ))}
          </div>
        ) : null}
        {error ? (
          <span className="composer__error" role="alert">
            {error}
          </span>
        ) : null}
        {dragging ? <div className="composer__drop">Drop files to attach</div> : null}
        <div className="composer__input">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            hidden
            onChange={handleFiles}
            aria-label="Choose attachments"
          />
          <IconButton
            label="Add attachments"
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={Boolean(disabledReason) || !allowMedia}
          >
            <Paperclip size={19} />
          </IconButton>
          <textarea
            rows={1}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={Boolean(disabledReason)}
            placeholder={disabledReason ?? `Message ${targetName}`}
            aria-label={`Message ${targetName}`}
          />
          <IconButton
            label="Schedule message"
            type="button"
            onClick={openSchedule}
            disabled={Boolean(disabledReason) || (!text.trim() && !attachments.length)}
          >
            <CalendarClock size={19} />
          </IconButton>
          <IconButton
            label="Send message"
            className="composer__send"
            type="submit"
            disabled={
              sending ||
              Boolean(disabledReason) ||
              (!text.trim() && !attachments.length)
            }
          >
            <Send size={18} />
          </IconButton>
        </div>
        <small className="composer__hint">
          Enter to send · Shift + Enter for a new line
        </small>
      </form>

      <Modal
        open={scheduleOpen}
        onClose={() => setScheduleOpen(false)}
        title="Schedule this message"
        description="It will be sent even when you are offline."
        width="small"
        footer={
          <>
            <Button variant="secondary" onClick={() => setScheduleOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="schedule-form" busy={sending}>
              Schedule message
            </Button>
          </>
        }
      >
        <form id="schedule-form" onSubmit={handleSchedule}>
          <Field label="Send date and time" hint="Shown in your local timezone.">
            <input
              type="datetime-local"
              min={minimumScheduleTime}
              value={scheduleTime}
              onChange={(event) => setScheduleTime(event.target.value)}
              required
            />
          </Field>
        </form>
      </Modal>
    </>
  );
}
