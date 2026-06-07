alter table public.sessions
  add column if not exists call_context jsonb not null default '{}'::jsonb;

create table public.session_images (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.sessions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  storage_path text not null,
  mime_type text not null,
  status text not null default 'staged' check (status in ('staged', 'sent')),
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create index session_images_session_status_idx
  on public.session_images (session_id, status);

alter table public.session_images enable row level security;

create policy "Users read own session images"
  on public.session_images for select using (auth.uid() = user_id);

create policy "Users insert images for own active sessions"
  on public.session_images for insert with check (
    auth.uid() = user_id
    and exists (
      select 1 from public.sessions s
      where s.id = session_images.session_id
        and s.user_id = auth.uid()
        and s.status = 'active'
    )
  );

create policy "Users update own session images"
  on public.session_images for update using (auth.uid() = user_id);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'session-images',
  'session-images',
  false,
  5242880,
  array['image/jpeg', 'image/png', 'image/webp']
)
on conflict (id) do nothing;

create policy "Users upload session images"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'session-images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "Users read own session images storage"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'session-images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
