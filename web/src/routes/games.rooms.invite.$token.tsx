import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate, useParams } from '@tanstack/react-router'

import { api } from '../lib/api'

export const Route = createFileRoute('/games/rooms/invite/$token')({
  component: RoomInviteScreen,
})

function RoomInviteScreen() {
  const { token } = useParams({ from: '/games/rooms/invite/$token' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const invite = useQuery({
    queryKey: ['room-invite', token],
    queryFn: () => api.roomInvite(token),
    retry: false,
  })
  const currentUser = useQuery({
    queryKey: ['me'],
    queryFn: api.me,
    retry: false,
  })
  const join = useMutation({
    mutationFn: () => api.joinRoomInvite(token),
    onSuccess: (room) => navigate({ to: '/games/rooms/$roomId', params: { roomId: String(room.id) } }),
  })
  const joinGuest = useMutation({
    mutationFn: () => api.joinGuestRoom(token, name.trim(), email.trim()),
    onSuccess: async (result) => {
      queryClient.setQueryData(['me'], result.user)
      await navigate({ to: '/games/rooms/$roomId', params: { roomId: String(result.room.id) } })
    },
  })
  const error = invite.error || join.error || joinGuest.error
  const isLoggedIn = Boolean(currentUser.data)

  if (invite.isLoading) {
    return <main className="public-room-invite page-content"><p>Loading your game invitation…</p></main>
  }
  if (!invite.data || invite.error) {
    return <main className="public-room-invite page-content"><section className="auth-card"><span className="eyebrow">Game room</span><h1>This invitation has expired</h1><p className="muted-text">Ask the host for a fresh room link.</p></section></main>
  }

  const room = invite.data
  const busy = join.isPending || joinGuest.isPending
  return <main className="public-room-invite page-content">
    <section className="auth-card public-room-invite__card">
      <span className="eyebrow">You’re invited to play</span>
      <h1>{room.name}</h1>
      <p className="muted-text">{room.game} · {room.players} of {room.max_players} seats filled</p>
      {room.status === 'active' && <p className="form-error" role="alert">This game has already started. Ask the host to invite you to the next round.</p>}
      {room.status === 'open' && isLoggedIn && <button className="button button--primary" type="button" disabled={busy} onClick={() => join.mutate()}>{join.isPending ? 'Joining…' : 'Join room'}</button>}
      {room.status === 'open' && !isLoggedIn && <form onSubmit={(event) => { event.preventDefault(); if (name.trim() && email.trim()) joinGuest.mutate() }}>
        <label className="field-label" htmlFor="guest-name">Your full name</label>
        <input id="guest-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={80} required placeholder="e.g. Alex" />
        <label className="field-label" htmlFor="guest-email">Email for your results</label>
        <input id="guest-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required placeholder="you@example.com" />
        <p className="muted-text">Your marked result will be sent to this address after grading.</p>
        <button className="button button--primary" type="submit" disabled={busy || name.trim().length < 2 || !email.includes('@')}>{joinGuest.isPending ? 'Joining…' : 'Join exam lobby'}</button>
      </form>}
      {error && <p className="form-error" role="alert">{error instanceof Error ? error.message : 'We could not join this room.'}</p>}
    </section>
  </main>
}
