import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, useNavigate, useParams } from '@tanstack/react-router'
import { Eye } from '@phosphor-icons/react'

import { api } from '../lib/api'

export const Route = createFileRoute('/games/rooms/invite/$token')({
  component: RoomInviteScreen,
})

function RoomInviteScreen() {
  const { token } = useParams({ from: '/games/rooms/invite/$token' })
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
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
    mutationFn: () => api.joinGuestRoom(token, name.trim()),
    onSuccess: async (result) => {
      queryClient.setQueryData(['me'], result.user)
      await navigate({ to: '/games/rooms/$roomId', params: { roomId: String(result.room.id) } })
    },
  })
  const spectateGuest = useMutation({
    mutationFn: () => api.spectateGuestRoom(token, name.trim()),
    onSuccess: async (result) => {
      queryClient.setQueryData(['me'], result.user)
      if (!result.room.match_id) return
      await navigate({
        to: result.room.game === 'Connect Four' ? '/games/play/$matchId' : '/games/session/$matchId',
        params: { matchId: result.room.match_id },
      })
    },
  })
  const error = invite.error || join.error || joinGuest.error || spectateGuest.error
  const isLoggedIn = Boolean(currentUser.data)

  if (invite.isLoading) {
    return <main className="public-room-invite page-content"><p>Loading your game invitation…</p></main>
  }
  if (!invite.data || invite.error) {
    return <main className="public-room-invite page-content"><section className="auth-card"><span className="eyebrow">Game room</span><h1>This invitation has expired</h1><p className="muted-text">Ask the host for a fresh room link.</p></section></main>
  }

  const room = invite.data
  const busy = join.isPending || joinGuest.isPending || spectateGuest.isPending
  return <main className="public-room-invite page-content">
    <section className="auth-card public-room-invite__card">
      <span className="eyebrow">You’re invited to play</span>
      <h1>{room.name}</h1>
      <p className="muted-text">{room.game} · {room.players} of {room.max_players} seats filled</p>
      {room.status === 'active' && <p className="spectator-banner" role="status"><Eye size={18} aria-hidden="true" /> This game is live. You can watch without taking a player seat.</p>}
      {room.status === 'active' && room.match_id && isLoggedIn && <button className="button button--primary" type="button" disabled={busy} onClick={() => void navigate({ to: room.game === 'Connect Four' ? '/games/play/$matchId' : '/games/session/$matchId', params: { matchId: room.match_id! } })}><Eye size={18} /> Watch live game</button>}
      {room.status === 'open' && isLoggedIn && <button className="button button--primary" type="button" disabled={busy} onClick={() => join.mutate()}>{join.isPending ? 'Joining…' : 'Join room'}</button>}
      {room.status === 'open' && !isLoggedIn && <form onSubmit={(event) => { event.preventDefault(); if (name.trim()) joinGuest.mutate() }}>
        <label className="field-label" htmlFor="guest-name">Your display name</label>
        <input id="guest-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={80} required placeholder="e.g. Alex" />
        <button className="button button--primary" type="submit" disabled={busy || name.trim().length < 2}>{joinGuest.isPending ? 'Joining…' : 'Join as guest'}</button>
      </form>}
      {room.status === 'active' && !isLoggedIn && <form onSubmit={(event) => { event.preventDefault(); if (name.trim()) spectateGuest.mutate() }}>
        <label className="field-label" htmlFor="guest-name">Your display name</label>
        <input id="guest-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={80} required placeholder="e.g. Alex" />
        <button className="button button--primary" type="submit" disabled={busy || name.trim().length < 2}>{spectateGuest.isPending ? 'Opening game…' : 'Watch as guest'}</button>
      </form>}
      {error && <p className="form-error" role="alert">{error instanceof Error ? error.message : 'We could not join this room.'}</p>}
    </section>
  </main>
}
