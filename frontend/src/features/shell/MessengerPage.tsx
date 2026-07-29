import { useCallback, useEffect, useState } from "react";
import {
  Hash,
  MessageCircle,
  MessageSquareText,
  Plus,
  Users,
} from "lucide-react";

import { messagesApi, notificationsApi, spacesApi } from "../../api/endpoints";
import {
  noPermissions,
  type Message,
  type Notification,
  type RealtimeEvent,
  type Space,
  type SpaceMember,
  type Topic,
} from "../../api/types";
import {
  Button,
  EmptyState,
  ErrorNotice,
  LoadingState,
} from "../../components/ui";
import { useToast } from "../../components/ToastProvider";
import { useRealtime } from "../../socket/useRealtime";
import { useAuth } from "../auth/AuthContext";
import { CreateSpaceModal } from "../spaces/CreateSpaceModal";
import { ProfileModal } from "../profile/ProfileModal";
import { SpaceSettingsModal } from "../spaces/SpaceSettingsModal";
import { MessageComposer } from "../messages/MessageComposer";
import { MessageList } from "../messages/MessageList";
import {
  applyMessageEvent,
  mergeMessage,
  sortMessages,
} from "../messages/messageState";
import { ScheduledPanel } from "../messages/ScheduledPanel";
import { SearchPanel } from "../messages/SearchPanel";
import {
  NotificationPanel,
  notificationText,
} from "../notifications/NotificationPanel";
import { ChatHeader } from "./ChatHeader";
import { MemberRail } from "./MemberRail";
import { SpaceSidebar } from "./SpaceSidebar";

type SidePanel = "search" | "scheduled" | "notifications" | null;

function eventMessage(event: RealtimeEvent): Message | null {
  if (
    !["message.created", "message.updated", "scheduled_message.sent"].includes(
      event.type,
    )
  ) {
    return null;
  }
  return event.payload as Message;
}

function uniqueMessages(messages: Message[]): Message[] {
  return sortMessages([
    ...new Map(messages.map((message) => [message.id, message])).values(),
  ]);
}

export function MessengerPage() {
  const { user, logout } = useAuth();
  const { showToast } = useToast();

  const [spaces, setSpaces] = useState<Space[]>([]);
  const [selectedSpaceId, setSelectedSpaceId] = useState<string | null>(
    () => window.localStorage.getItem("echo:selected-space"),
  );
  const [topics, setTopics] = useState<Topic[]>([]);
  const [selectedTopicId, setSelectedTopicId] = useState<string | null>(null);
  const [members, setMembers] = useState<SpaceMember[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [nextMessagesPage, setNextMessagesPage] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const [loadingSpaces, setLoadingSpaces] = useState(true);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const [sending, setSending] = useState(false);

  const [spacesError, setSpacesError] = useState<string | null>(null);
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [notificationError, setNotificationError] = useState<string | null>(
    null,
  );

  const [navigationOpen, setNavigationOpen] = useState(false);
  const [membersOpen, setMembersOpen] = useState(true);
  const [sidePanel, setSidePanel] = useState<SidePanel>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [profileUserId, setProfileUserId] = useState<string | null>(null);
  const [detailsVersion, setDetailsVersion] = useState(0);
  const [spacesVersion, setSpacesVersion] = useState(0);

  const selectedSpace =
    spaces.find((space) => space.id === selectedSpaceId) ?? null;
  const selectedTopic =
    topics.find((topic) => topic.id === selectedTopicId) ?? undefined;
  const selectedSpaceType = selectedSpace?.type;
  const permissions = selectedSpace
    ? selectedSpace.my_permissions
    : noPermissions;

  const loadSpaces = useCallback(() => {
    let active = true;
    setLoadingSpaces(true);
    setSpacesError(null);
    spacesApi
      .list()
      .then((page) => {
        if (!active) return;
        setSpaces(page.results);
        setSelectedSpaceId((current) => {
          if (current && page.results.some((space) => space.id === current)) {
            return current;
          }
          return page.results[0]?.id ?? null;
        });
      })
      .catch((reason) => {
        if (active) {
          setSpacesError(
            reason instanceof Error
              ? reason.message
              : "Could not load conversations.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingSpaces(false);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(loadSpaces, [loadSpaces, spacesVersion]);

  useEffect(() => {
    if (selectedSpaceId) {
      window.localStorage.setItem("echo:selected-space", selectedSpaceId);
    } else {
      window.localStorage.removeItem("echo:selected-space");
    }
  }, [selectedSpaceId]);

  useEffect(() => {
    if (!selectedSpaceId || !selectedSpaceType) {
      setMembers([]);
      setTopics([]);
      setSelectedTopicId(null);
      return;
    }

    let active = true;
    setLoadingDetails(true);
    const memberRequest = spacesApi.members(selectedSpaceId);
    const topicRequest =
      selectedSpaceType === "CHANNEL"
        ? spacesApi.topics(selectedSpaceId)
        : Promise.resolve({ results: [], next: null, previous: null });

    Promise.all([memberRequest, topicRequest])
      .then(([memberPage, topicPage]) => {
        if (!active) return;
        setMembers(memberPage.results);
        setTopics(topicPage.results);
        setSelectedTopicId((current) => {
          if (selectedSpaceType !== "CHANNEL") return null;
          if (current && topicPage.results.some((topic) => topic.id === current)) {
            return current;
          }
          return topicPage.results[0]?.id ?? null;
        });
      })
      .catch((reason) => {
        if (active) {
          showToast(
            reason instanceof Error
              ? reason.message
              : "Could not load conversation details.",
            "error",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingDetails(false);
      });

    return () => {
      active = false;
    };
  }, [detailsVersion, selectedSpaceId, selectedSpaceType, showToast]);

  useEffect(() => {
    if (
      !selectedSpaceId ||
      (selectedSpaceType === "CHANNEL" && !selectedTopicId)
    ) {
      setMessages([]);
      setNextMessagesPage(null);
      setLoadingMessages(false);
      return;
    }

    let active = true;
    setLoadingMessages(true);
    setMessagesError(null);
    messagesApi
      .list(selectedSpaceId, selectedTopicId)
      .then((page) => {
        if (!active) return;
        setMessages(sortMessages(page.results));
        setNextMessagesPage(page.next);
      })
      .catch((reason) => {
        if (active) {
          setMessagesError(
            reason instanceof Error ? reason.message : "Could not load messages.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingMessages(false);
      });

    return () => {
      active = false;
    };
  }, [selectedSpaceId, selectedSpaceType, selectedTopicId]);

  useEffect(() => {
    let active = true;
    setLoadingNotifications(true);
    notificationsApi
      .list()
      .then((page) => {
        if (active) setNotifications(page.results);
      })
      .catch((reason) => {
        if (active) {
          setNotificationError(
            reason instanceof Error
              ? reason.message
              : "Could not load notifications.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingNotifications(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const handleSpaceEvent = useCallback(
    (event: RealtimeEvent) => {
      const incoming = eventMessage(event);
      if (incoming) {
        const belongsToVisibleConversation =
          incoming.space === selectedSpaceId &&
          (!selectedTopicId || incoming.topic_id === selectedTopicId);

        if (belongsToVisibleConversation) {
          setMessages((current) => applyMessageEvent(current, event));
        } else if (event.type === "message.created") {
          setSpaces((current) =>
            current.map((space) =>
              space.id === incoming.space
                ? { ...space, unread_count: (space.unread_count ?? 0) + 1 }
                : space,
            ),
          );
        }
      } else if (event.type === "message.deleted") {
        setMessages((current) => applyMessageEvent(current, event));
      } else if (event.type === "space.updated") {
        setSpacesVersion((value) => value + 1);
        setDetailsVersion((value) => value + 1);
      } else if (event.type === "member.updated") {
        setSpacesVersion((value) => value + 1);
        setDetailsVersion((value) => value + 1);
      }
    },
    [selectedSpaceId, selectedTopicId],
  );

  const handleNotificationEvent = useCallback(
    (event: RealtimeEvent) => {
      if (event.type === "member.updated") {
        setSpacesVersion((value) => value + 1);
        setDetailsVersion((value) => value + 1);
        return;
      }
      if (event.type !== "notification.created") return;
      const notification = event.payload as Notification;
      setNotifications((current) => [
        notification,
        ...current.filter((item) => item.id !== notification.id),
      ]);
      if (
        notification.event_type === "MESSAGE_CREATED" &&
        notification.space_id !== selectedSpaceId
      ) {
        setSpaces((current) =>
          current.map((space) =>
            space.id === notification.space_id
              ? { ...space, unread_count: (space.unread_count ?? 0) + 1 }
              : space,
          ),
        );
      }
      showToast(notificationText(notification));
    },
    [selectedSpaceId, showToast],
  );

  const spaceConnection = useRealtime(
    selectedSpace ? `/ws/spaces/${selectedSpace.id}/` : null,
    handleSpaceEvent,
  );
  useRealtime("/ws/notifications/", handleNotificationEvent);

  function selectSpace(space: Space) {
    setSelectedSpaceId(space.id);
    setSelectedTopicId(null);
    setNavigationOpen(false);
    setSidePanel(null);
    setSpaces((current) =>
      current.map((item) =>
        item.id === space.id ? { ...item, unread_count: 0 } : item,
      ),
    );
  }

  async function loadOlderMessages() {
    if (!selectedSpace || !nextMessagesPage) return;
    setLoadingOlder(true);
    try {
      const page = await messagesApi.list(
        selectedSpace.id,
        selectedTopicId,
        nextMessagesPage,
      );
      setMessages((current) => uniqueMessages([...page.results, ...current]));
      setNextMessagesPage(page.next);
    } catch (reason) {
      showToast(
        reason instanceof Error ? reason.message : "Could not load older messages.",
        "error",
      );
    } finally {
      setLoadingOlder(false);
    }
  }

  async function sendMessage(
    text: string,
    attachments: File[],
    scheduledFor?: string,
  ) {
    if (!selectedSpace) return;
    setSending(true);
    try {
      const created = await messagesApi.create(selectedSpace.id, {
        text,
        topic_id: selectedTopicId,
        attachments,
        scheduled_for: scheduledFor,
        client_nonce: crypto.randomUUID(),
      });
      if (created.status === "PENDING") {
        showToast("Message scheduled.", "success");
      } else {
        setMessages((current) => mergeMessage(current, created));
      }
    } finally {
      setSending(false);
    }
  }

  async function editMessage(messageId: string, text: string) {
    const updated = await messagesApi.update(messageId, text);
    setMessages((current) => mergeMessage(current, updated));
    showToast("Message updated.", "success");
  }

  async function deleteMessage(messageId: string) {
    await messagesApi.remove(messageId);
    setMessages((current) =>
      current.filter((message) => message.id !== messageId),
    );
    showToast("Message deleted.", "success");
  }

  function handleSpaceCreated(space: Space) {
    setSpaces((current) => [
      space,
      ...current.filter((item) => item.id !== space.id),
    ]);
    setSelectedSpaceId(space.id);
    setSelectedTopicId(null);
  }

  function handleSpaceDeleted(spaceId: string) {
    setSpaces((current) => {
      const remaining = current.filter((space) => space.id !== spaceId);
      setSelectedSpaceId(remaining[0]?.id ?? null);
      return remaining;
    });
    setSettingsOpen(false);
  }

  async function handleNotification(notification: Notification) {
    if (!notification.is_read) {
      try {
        const updated = await notificationsApi.markRead(notification.id);
        setNotifications((current) =>
          current.map((item) => (item.id === updated.id ? updated : item)),
        );
      } catch (reason) {
        showToast(
          reason instanceof Error
            ? reason.message
            : "Could not mark notification as read.",
          "error",
        );
      }
    }
    if (notification.space_id) {
      const space = spaces.find((item) => item.id === notification.space_id);
      if (space) selectSpace(space);
    }
    setSidePanel(null);
  }

  async function readAllNotifications() {
    try {
      await notificationsApi.readAll();
      const now = new Date().toISOString();
      setNotifications((current) =>
        current.map((item) => ({
          ...item,
          is_read: true,
          read_at: item.read_at ?? now,
        })),
      );
    } catch (reason) {
      showToast(
        reason instanceof Error ? reason.message : "Could not mark notifications.",
        "error",
      );
    }
  }

  function togglePanel(panel: Exclude<SidePanel, null>) {
    setSidePanel((current) => (current === panel ? null : panel));
    setMembersOpen(false);
  }

  async function handleLogout() {
    try {
      await logout();
    } catch (reason) {
      showToast(
        reason instanceof Error ? reason.message : "Could not log out.",
        "error",
      );
    }
  }

  const unreadNotifications = notifications.filter(
    (notification) => !notification.is_read,
  ).length;
  const composerReason = !permissions.can_send_messages
    ? "You do not have permission to send messages here."
    : selectedSpace?.type === "CHANNEL" && !selectedTopic
      ? "Choose or create a topic before sending messages."
      : undefined;

  return (
    <main className="messenger">
      <SpaceSidebar
        spaces={spaces}
        selectedSpace={selectedSpace}
        topics={topics}
        selectedTopicId={selectedTopicId}
        currentUser={user!}
        loading={loadingSpaces}
        open={navigationOpen}
        connectionState={spaceConnection}
        onClose={() => setNavigationOpen(false)}
        onSelectSpace={selectSpace}
        onSelectTopic={(topicId) => {
          setSelectedTopicId(topicId);
          setNavigationOpen(false);
        }}
        onCreate={() => setCreateOpen(true)}
        onSettings={() => setSettingsOpen(true)}
        onProfile={() => setProfileUserId(user!.id)}
        onLogout={handleLogout}
      />

      <section className="conversation-shell">
        {spacesError ? (
          <div className="conversation-shell__error">
            <ErrorNotice
              message={spacesError}
              onRetry={() => setSpacesVersion((value) => value + 1)}
            />
          </div>
        ) : null}

        {!selectedSpace && !loadingSpaces ? (
          <WelcomePanel onCreate={() => setCreateOpen(true)} />
        ) : selectedSpace ? (
          <>
            <ChatHeader
              space={selectedSpace}
              topic={selectedTopic}
              connectionState={spaceConnection}
              unreadNotifications={unreadNotifications}
              activePanel={sidePanel}
              onOpenNavigation={() => setNavigationOpen(true)}
              onToggleSearch={() => togglePanel("search")}
              onToggleScheduled={() => togglePanel("scheduled")}
              onToggleNotifications={() => togglePanel("notifications")}
              onToggleMembers={() => {
                setMembersOpen((open) => !open);
                setSidePanel(null);
              }}
            />
            <div className="conversation">
              <section className="chat-column" aria-label="Conversation">
                {loadingDetails &&
                selectedSpace.type === "CHANNEL" &&
                !selectedTopic ? (
                  <LoadingState label="Loading topics" />
                ) : selectedSpace.type === "CHANNEL" && !selectedTopic ? (
                  <EmptyState
                    title="This channel needs a topic"
                    description="Topics keep channel conversations organized."
                    action={
                      permissions.can_manage_topics ? (
                        <Button onClick={() => setSettingsOpen(true)}>
                          <Plus size={16} /> Create a topic
                        </Button>
                      ) : undefined
                    }
                  />
                ) : (
                  <>
                    <MessageList
                      messages={messages}
                      currentUserId={user!.id}
                      permissions={permissions}
                      loading={loadingMessages}
                      loadingOlder={loadingOlder}
                      error={messagesError}
                      hasOlder={Boolean(nextMessagesPage)}
                      onLoadOlder={loadOlderMessages}
                      onEdit={editMessage}
                      onDelete={deleteMessage}
                      onOpenProfile={setProfileUserId}
                    />
                    <MessageComposer
                      targetName={
                        selectedTopic
                          ? `#${selectedTopic.name}`
                          : selectedSpace.display_name
                      }
                      disabledReason={composerReason}
                      allowMedia={permissions.can_send_media}
                      sending={sending}
                      onSend={sendMessage}
                    />
                  </>
                )}
              </section>

              <SearchPanel
                open={sidePanel === "search"}
                spaceId={selectedSpace.id}
                topicId={selectedTopicId}
                onClose={() => setSidePanel(null)}
                onOpenProfile={setProfileUserId}
              />
              <ScheduledPanel
                open={sidePanel === "scheduled"}
                onClose={() => setSidePanel(null)}
              />
              <NotificationPanel
                open={sidePanel === "notifications"}
                notifications={notifications}
                loading={loadingNotifications}
                error={notificationError}
                onClose={() => setSidePanel(null)}
                onRead={handleNotification}
                onReadAll={readAllNotifications}
              />
              <MemberRail
                members={members}
                ownerId={selectedSpace.created_by.id}
                open={membersOpen && !sidePanel}
                onClose={() => setMembersOpen(false)}
                onOpenProfile={setProfileUserId}
              />
            </div>
          </>
        ) : (
          <LoadingState label="Opening conversation" />
        )}
      </section>

      <CreateSpaceModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={handleSpaceCreated}
      />
      <ProfileModal
        userId={profileUserId}
        onClose={() => setProfileUserId(null)}
      />
      <SpaceSettingsModal
        space={settingsOpen ? selectedSpace : null}
        currentUserId={user!.id}
        members={members}
        topics={topics}
        onClose={() => setSettingsOpen(false)}
        onUpdated={(updated) =>
          setSpaces((current) =>
            current.map((space) => (space.id === updated.id ? updated : space)),
          )
        }
        onDeleted={handleSpaceDeleted}
        onDetailsChanged={() => setDetailsVersion((value) => value + 1)}
      />
    </main>
  );
}

function WelcomePanel({ onCreate }: { onCreate: () => void }) {
  return (
    <section className="welcome-panel">
      <span className="welcome-panel__mark">
        <MessageSquareText size={31} />
      </span>
      <span className="eyebrow">Your conversations</span>
      <h1>Start somewhere simple.</h1>
      <p>
        Message one person, gather a private group, or create a channel with
        topics and roles.
      </p>
      <Button onClick={onCreate}>
        <Plus size={17} aria-hidden /> Start a conversation
      </Button>
      <div className="welcome-panel__options" aria-hidden>
        <span>
          <MessageCircle size={18} /> Direct
        </span>
        <span>
          <Users size={18} /> Group
        </span>
        <span>
          <Hash size={18} /> Channel
        </span>
      </div>
    </section>
  );
}
