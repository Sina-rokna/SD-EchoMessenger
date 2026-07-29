import { Bell, CheckCheck, MessageSquareText, X } from "lucide-react";

import type { Notification } from "../../api/types";
import {
  Avatar,
  Button,
  EmptyState,
  ErrorNotice,
  IconButton,
  LoadingState,
} from "../../components/ui";
import { formatRelativeTime } from "../../utils/format";

interface NotificationPanelProps {
  open: boolean;
  notifications: Notification[];
  loading: boolean;
  error: string | null;
  onClose: () => void;
  onRead: (notification: Notification) => void;
  onReadAll: () => void;
}

export function notificationText(notification: Notification): string {
  const actor = notification.actor?.username ?? "Someone";
  if (notification.event_type === "MESSAGE_CREATED") {
    return `${actor} sent a new message.`;
  }
  if (notification.event_type === "MEMBER_ADDED") {
    return `${actor} added you to a space.`;
  }
  return "You have a new EchoMessenger update.";
}

export function NotificationPanel({
  open,
  notifications,
  loading,
  error,
  onClose,
  onRead,
  onReadAll,
}: NotificationPanelProps) {
  if (!open) return null;
  const unread = notifications.filter((item) => !item.is_read).length;

  return (
    <aside className="side-panel" aria-label="Notifications">
      <header className="side-panel__header">
        <div>
          <span className="eyebrow">Inbox</span>
          <h2>Notifications</h2>
        </div>
        <IconButton label="Close notifications" onClick={onClose}>
          <X size={18} />
        </IconButton>
      </header>
      {unread ? (
        <div className="side-panel__toolbar">
          <span>{unread} unread</span>
          <Button variant="ghost" onClick={onReadAll}>
            <CheckCheck size={16} aria-hidden /> Mark all read
          </Button>
        </div>
      ) : null}
      <div className="side-panel__content">
        {error ? <ErrorNotice message={error} /> : null}
        {loading ? <LoadingState label="Loading notifications" /> : null}
        {!loading && !notifications.length ? (
          <EmptyState
            title="All caught up"
            description="New message and membership updates will appear here."
          />
        ) : (
          <ol className="notification-list">
            {notifications.map((notification) => (
              <li
                key={notification.id}
                className={!notification.is_read ? "is-unread" : ""}
              >
                <button onClick={() => onRead(notification)}>
                  <span className="notification-list__avatar">
                    {notification.actor ? (
                      <Avatar user={notification.actor} size="small" />
                    ) : notification.event_type === "MESSAGE_CREATED" ? (
                      <MessageSquareText size={18} />
                    ) : (
                      <Bell size={18} />
                    )}
                  </span>
                  <span>
                    <strong>{notificationText(notification)}</strong>
                    <time dateTime={notification.created_at}>
                      {formatRelativeTime(notification.created_at)}
                    </time>
                  </span>
                  {!notification.is_read ? (
                    <i className="unread-dot" aria-label="Unread" />
                  ) : null}
                </button>
              </li>
            ))}
          </ol>
        )}
      </div>
    </aside>
  );
}
