import {
  Bell,
  CalendarClock,
  Hash,
  Menu,
  Search,
  Users,
} from "lucide-react";

import type { Space, Topic } from "../../api/types";
import { IconButton } from "../../components/ui";
import type { ConnectionState } from "../../socket/useRealtime";

interface ChatHeaderProps {
  space: Space;
  topic?: Topic;
  connectionState: ConnectionState;
  unreadNotifications: number;
  activePanel: string | null;
  onOpenNavigation: () => void;
  onToggleSearch: () => void;
  onToggleScheduled: () => void;
  onToggleNotifications: () => void;
  onToggleMembers: () => void;
}

export function ChatHeader({
  space,
  topic,
  connectionState,
  unreadNotifications,
  activePanel,
  onOpenNavigation,
  onToggleSearch,
  onToggleScheduled,
  onToggleNotifications,
  onToggleMembers,
}: ChatHeaderProps) {
  const title = topic ? topic.name : space.display_name;

  return (
    <header className="chat-header">
      <IconButton
        label="Open navigation"
        className="chat-header__menu"
        onClick={onOpenNavigation}
      >
        <Menu size={19} />
      </IconButton>
      <div className="chat-header__title">
        {topic || space.type === "CHANNEL" ? (
          <Hash size={20} aria-hidden />
        ) : space.type === "GROUP" ? (
          <Users size={20} aria-hidden />
        ) : null}
        <span>
          <strong>{title}</strong>
          <small>
            {connectionState === "connected"
              ? space.type === "CHANNEL"
                ? space.display_name
                : "Live conversation"
              : "Reconnecting to live updates…"}
          </small>
        </span>
      </div>
      <div className="chat-header__actions">
        <IconButton
          label="Search messages"
          active={activePanel === "search"}
          onClick={onToggleSearch}
        >
          <Search size={18} />
        </IconButton>
        <IconButton
          label="Scheduled messages"
          active={activePanel === "scheduled"}
          onClick={onToggleScheduled}
        >
          <CalendarClock size={18} />
        </IconButton>
        <IconButton
          label="Notifications"
          active={activePanel === "notifications"}
          className="badge-button"
          onClick={onToggleNotifications}
        >
          <Bell size={18} />
          {unreadNotifications ? (
            <b aria-label={`${unreadNotifications} unread notifications`}>
              {unreadNotifications > 9 ? "9+" : unreadNotifications}
            </b>
          ) : null}
        </IconButton>
        <IconButton label="Show members" onClick={onToggleMembers}>
          <Users size={19} />
        </IconButton>
      </div>
    </header>
  );
}
