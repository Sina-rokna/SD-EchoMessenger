import {
  ChevronDown,
  Hash,
  LogOut,
  MessageCircle,
  MessageSquareText,
  Plus,
  Settings,
  Users,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";

import type { Space, Topic, User } from "../../api/types";
import { Avatar, IconButton, LoadingState } from "../../components/ui";
import type { ConnectionState } from "../../socket/useRealtime";

interface SpaceSidebarProps {
  spaces: Space[];
  selectedSpace: Space | null;
  topics: Topic[];
  selectedTopicId: string | null;
  currentUser: User;
  loading: boolean;
  open: boolean;
  connectionState: ConnectionState;
  onClose: () => void;
  onSelectSpace: (space: Space) => void;
  onSelectTopic: (topicId: string) => void;
  onCreate: () => void;
  onSettings: () => void;
  onProfile: () => void;
  onLogout: () => void;
}

const sectionMeta = {
  DIRECT: { title: "Direct messages", icon: MessageCircle },
  GROUP: { title: "Groups", icon: Users },
  CHANNEL: { title: "Channels", icon: Hash },
} as const;

export function SpaceSidebar({
  spaces,
  selectedSpace,
  topics,
  selectedTopicId,
  currentUser,
  loading,
  open,
  connectionState,
  onClose,
  onSelectSpace,
  onSelectTopic,
  onCreate,
  onSettings,
  onProfile,
  onLogout,
}: SpaceSidebarProps) {
  return (
    <>
      {open ? (
        <button
          className="mobile-scrim"
          onClick={onClose}
          aria-label="Close navigation"
        />
      ) : null}
      <aside className={`space-sidebar ${open ? "is-open" : ""}`}>
        <header className="space-sidebar__brand">
          <span className="brand__mark">
            <MessageSquareText size={21} />
          </span>
          <strong>EchoMessenger</strong>
          <IconButton
            label="Close navigation"
            className="only-mobile"
            onClick={onClose}
          >
            <X size={18} />
          </IconButton>
        </header>

        <div className="space-sidebar__action">
          <button onClick={onCreate}>
            <Plus size={18} aria-hidden />
            Start a conversation
          </button>
        </div>

        <nav className="space-navigation" aria-label="Conversations">
          {loading ? <LoadingState label="Loading conversations" /> : null}
          {!loading && !spaces.length ? (
            <div className="space-navigation__empty">
              <MessageCircle size={20} />
              <strong>No conversations yet</strong>
              <p>Start a direct message, group, or channel.</p>
            </div>
          ) : null}
          {(["DIRECT", "GROUP", "CHANNEL"] as const).map((type) => {
            const items = spaces.filter((space) => space.type === type);
            if (!items.length) return null;
            const SectionIcon = sectionMeta[type].icon;
            return (
              <section className="space-section" key={type}>
                <h2>
                  <SectionIcon size={14} aria-hidden />
                  {sectionMeta[type].title}
                </h2>
                <ul>
                  {items.map((space) => {
                    const active = selectedSpace?.id === space.id;
                    return (
                      <li key={space.id}>
                        <button
                          className={`space-link ${active ? "is-active" : ""}`}
                          onClick={() => onSelectSpace(space)}
                          aria-current={active ? "page" : undefined}
                        >
                          <Avatar
                            name={space.display_name}
                            src={space.avatar_url}
                            size="small"
                          />
                          <span>
                            <strong>{space.display_name}</strong>
                            <small>
                              {type === "CHANNEL"
                                ? `${space.membership_count} members`
                                : "Open conversation"}
                            </small>
                          </span>
                          {space.unread_count ? (
                            <b aria-label={`${space.unread_count} unread`}>
                              {space.unread_count > 99 ? "99+" : space.unread_count}
                            </b>
                          ) : null}
                        </button>
                        {active && type === "CHANNEL" ? (
                          <div className="topic-navigation">
                            <div className="topic-navigation__header">
                              <span>
                                Topics <ChevronDown size={13} aria-hidden />
                              </span>
                              <IconButton
                                label="Channel settings"
                                onClick={onSettings}
                              >
                                <Settings size={14} />
                              </IconButton>
                            </div>
                            {topics.length ? (
                              <ul>
                                {topics.map((topic) => (
                                  <li key={topic.id}>
                                    <button
                                      className={
                                        selectedTopicId === topic.id
                                          ? "is-active"
                                          : ""
                                      }
                                      onClick={() => onSelectTopic(topic.id)}
                                    >
                                      <Hash size={15} aria-hidden />
                                      {topic.name}
                                    </button>
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <button
                                className="topic-navigation__empty"
                                onClick={onSettings}
                              >
                                Create the first topic
                              </button>
                            )}
                          </div>
                        ) : null}
                      </li>
                    );
                  })}
                </ul>
              </section>
            );
          })}
        </nav>

        {selectedSpace && selectedSpace.type !== "CHANNEL" ? (
          <button className="space-settings-link" onClick={onSettings}>
            <Settings size={16} aria-hidden />
            {selectedSpace.type === "GROUP" ? "Group settings" : "Conversation info"}
          </button>
        ) : null}

        <footer className="account-bar">
          <button className="account-bar__profile" onClick={onProfile}>
            <Avatar user={currentUser} size="small" online />
            <span>
              <strong>{currentUser.username}</strong>
              <small>
                {connectionState === "connected" ? (
                  <>
                    <Wifi size={11} aria-hidden /> Connected
                  </>
                ) : (
                  <>
                    <WifiOff size={11} aria-hidden /> Reconnecting
                  </>
                )}
              </small>
            </span>
          </button>
          <IconButton label="Log out" onClick={onLogout}>
            <LogOut size={17} />
          </IconButton>
        </footer>
      </aside>
    </>
  );
}
