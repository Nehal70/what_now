create type public.session_status as enum ('active', 'completed');

create table public.profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  phone_e164 text unique not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  status public.session_status not null default 'active',
  caller_phone text not null,
  livekit_room text,
  phase text,
  title text,
  started_at timestamptz not null default now(),
  ended_at timestamptz
);

create index sessions_user_started_idx on public.sessions (user_id, started_at desc);

create index sessions_user_active_idx on public.sessions (user_id, status)
  where status = 'active';

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  text text not null,
  created_at timestamptz not null default now()
);

create index messages_session_created_idx on public.messages (session_id, created_at asc);

alter table public.profiles enable row level security;
alter table public.sessions enable row level security;
alter table public.messages enable row level security;

create policy "Users read own profile"
  on public.profiles for select using (auth.uid() = user_id);

create policy "Users insert own profile"
  on public.profiles for insert with check (auth.uid() = user_id);

create policy "Users update own profile"
  on public.profiles for update using (auth.uid() = user_id);

create policy "Users read own sessions"
  on public.sessions for select using (auth.uid() = user_id);

create policy "Users read messages for own sessions"
  on public.messages for select using (
    exists (
      select 1 from public.sessions s
      where s.id = messages.session_id and s.user_id = auth.uid()
    )
  );

alter publication supabase_realtime add table public.sessions;
alter publication supabase_realtime add table public.messages;
