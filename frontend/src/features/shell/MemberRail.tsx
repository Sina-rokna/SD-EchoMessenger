import type { ReactNode } from "react";
import { Shield, Users, X } from "lucide-react";

import type { SpaceMember } from "../../api/types";
import { Avatar, EmptyState, IconButton } from "../../components/ui";

interface MemberRailProps {
  members: SpaceMember[];
  ownerId: string;
  open: boolean;
  onClose: () => void;
  onOpenProfile: (userId: string) => void;
}

export function MemberRail({
  members,
  ownerId,
  open,
  onClose,
  onOpenProfile,
}: MemberRailProps) {
  const owners = members.filter((member) => member.user.id === ownerId);
  const otherMembers = members.filter((member) => member.user.id !== ownerId);
  const roleGroups = new Map<string, SpaceMember[]>();

  otherMembers.forEach((member) => {
    const name = member.role?.name ?? "Members";
    roleGroups.set(name, [...(roleGroups.get(name) ?? []), member]);
  });

  return (
    <aside className={`member-rail ${open ? "is-open" : ""}`} aria-label="Members">
      <header>
        <div>
          <span className="eyebrow">People</span>
          <h2>
            Members <span>{members.length}</span>
          </h2>
        </div>
        <IconButton
          label="Close member list"
          className="member-rail__close"
          onClick={onClose}
        >
          <X size={17} />
        </IconButton>
      </header>

      <div className="member-rail__content">
        {!members.length ? (
          <EmptyState
            title="No members to show"
            description="Member information will appear here."
          />
        ) : (
          <>
            {owners.length ? (
              <MemberGroup
                title="Owner"
                icon={<Shield size={13} />}
                members={owners}
                onOpenProfile={onOpenProfile}
              />
            ) : null}
            {[...roleGroups.entries()].map(([name, groupedMembers]) => (
              <MemberGroup
                title={name}
                icon={<Users size={13} />}
                members={groupedMembers}
                onOpenProfile={onOpenProfile}
                key={name}
              />
            ))}
          </>
        )}
      </div>
    </aside>
  );
}

function MemberGroup({
  title,
  icon,
  members,
  onOpenProfile,
}: {
  title: string;
  icon: ReactNode;
  members: SpaceMember[];
  onOpenProfile: (userId: string) => void;
}) {
  return (
    <section className="member-group">
      <h3>
        {icon}
        {title} <span>— {members.length}</span>
      </h3>
      <ul>
        {members.map((member) => (
          <li key={member.user.id}>
            <button onClick={() => onOpenProfile(member.user.id)}>
              <Avatar
                user={member.user}
                size="small"
              />
              <span>
                <strong>{member.user.username}</strong>
                <small>View profile</small>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
