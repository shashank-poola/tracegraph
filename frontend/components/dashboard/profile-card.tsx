import Image from "next/image";
import { MapPin } from "lucide-react";
import { ContributionChart } from "@/components/dashboard/contribution-chart";
import type { GithubProfile } from "@/lib/api";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col">
      <span className="font-heading text-lg text-foreground">
        {value.toLocaleString()}
      </span>
      <span className="text-xs text-muted">{label}</span>
    </div>
  );
}

export function ProfileCard({ profile }: { profile: GithubProfile }) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border p-6">
      <Image
        src={profile.avatar_url}
        alt={profile.login}
        width={64}
        height={64}
        className="h-16 w-16 rounded-full border border-border"
      />
      <div className="flex flex-col gap-1">
        <h2 className="font-heading text-lg text-foreground">{profile.name}</h2>
        <a
          href={profile.html_url}
          target="_blank"
          rel="noreferrer"
          className="text-sm text-muted transition-colors hover:text-foreground"
        >
          @{profile.login}
        </a>
      </div>

      {profile.bio && (
        <p className="text-sm leading-6 text-muted">{profile.bio}</p>
      )}

      {profile.location && (
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <MapPin className="h-3.5 w-3.5" />
          {profile.location}
        </div>
      )}

      {profile.contributions && profile.contributions.days.length > 0 && (
        <ContributionChart
          total={profile.contributions.total}
          days={profile.contributions.days}
        />
      )}

      <div className="grid grid-cols-3 gap-4 border-t border-border pt-4">
        <Stat label="Repos" value={profile.public_repos} />
        <Stat label="Followers" value={profile.followers} />
        <Stat label="Tracked" value={profile.tracked_count} />
      </div>
    </div>
  );
}
