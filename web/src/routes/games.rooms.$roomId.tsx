import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createFileRoute, Link, useNavigate, useParams } from '@tanstack/react-router'
import { ArrowLeft, CheckCircle, Copy, GameController, UsersThree } from '@phosphor-icons/react'

import { GeneralLoader } from '../components/general-loader'
import { ApiError, api, apiRetryDelay, assetUrl, shouldRetryApiRequest } from '../lib/api'

export const Route = createFileRoute('/games/rooms/$roomId')({ component: GameRoomLobby })

function GameRoomLobby() {
  const { roomId: rawRoomId } = useParams({ from: '/games/rooms/$roomId' })
  const roomId = Number(rawRoomId)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [copied, setCopied] = useState(false)
  const [abcCapacity, setAbcCapacity] = useState(4)
  const [abcCategories, setAbcCategories] = useState('Animal, Place, Food, Thing')
  const [abcMajorityInvalid, setAbcMajorityInvalid] = useState(true)
  const [showExamStart, setShowExamStart] = useState(false)
  const room = useQuery({
    queryKey: ['room', roomId],
    queryFn: () => api.room(roomId),
    enabled: Number.isInteger(roomId) && roomId > 0,
    retry: shouldRetryApiRequest,
    retryDelay: apiRetryDelay,
    refetchInterval: 1500,
  })
  const participants = useQuery({
    queryKey: ['room-participants', roomId],
    queryFn: () => api.roomParticipants(roomId),
    enabled: Number.isInteger(roomId) && roomId > 0,
    retry: shouldRetryApiRequest,
    retryDelay: apiRetryDelay,
    refetchInterval: 1500,
  })
  const ready = useMutation({
    mutationFn: () => api.setRoomReady(roomId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room', roomId] })
      queryClient.invalidateQueries({ queryKey: ['room-participants', roomId] })
    },
  })
  const start = useMutation({
    mutationFn: async () => {
      if (!room.data) throw new Error('Room is still loading')
      if (room.data.game === 'Connect Four') {
        const match = await api.createMatch({
          room_id: roomId,
          with_bot: room.data.fill_with_bots,
          bot_difficulty: room.data.bot_difficulty,
        })
        return { kind: 'connect-four' as const, id: match.match_id }
      }
      const match = await api.createGameSession(roomId, room.data.fill_with_bots, room.data.bot_difficulty)
      return { kind: 'session' as const, id: match.match_id }
    },
    onSuccess: (match) => {
      if (room.data?.game.trim().toLowerCase() === 'csec it mock exam')
        navigate({ to: '/admin' })
      else if (match.kind === 'connect-four')
        navigate({ to: '/games/play/$matchId', params: { matchId: match.id } })
      else navigate({ to: '/games/session/$matchId', params: { matchId: match.id } })
    },
  })
  const endRoom = useMutation({
    mutationFn: () => api.endRoom(roomId),
    onSuccess: () => navigate({ to: '/games' }),
  })
  const saveAbcSettings = useMutation({
    mutationFn: () => api.updateAbcRoomSettings(roomId, {
      max_players: abcCapacity,
      categories: abcCategories.split(',').map((category) => category.trim()).filter(Boolean),
      majority_invalid: abcMajorityInvalid,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['room', roomId] })
      queryClient.invalidateQueries({ queryKey: ['room-participants', roomId] })
    },
  })

  useEffect(() => {
    if (!room.data || room.data.game !== 'ABC Fast or Slow') return
    setAbcCapacity(room.data.max_players)
    setAbcCategories((room.data.abc_categories ?? ['Animal', 'Place', 'Food', 'Thing']).join(', '))
    setAbcMajorityInvalid(room.data.abc_majority_invalid ?? true)
  }, [room.data])

  useEffect(() => {
    const current = room.data
    if (!current?.match_id) return
    if (current.is_host && current.game.trim().toLowerCase() === 'csec it mock exam') return
    if (current.game === 'Connect Four')
      navigate({ to: '/games/play/$matchId', params: { matchId: current.match_id }, replace: true })
    else navigate({ to: '/games/session/$matchId', params: { matchId: current.match_id }, replace: true })
  }, [navigate, room.data])

  useEffect(() => {
    if (!(room.error instanceof ApiError)) return
    if (room.error.status === 401) navigate({ to: '/login', replace: true })
    if (room.error.status === 404) navigate({ to: '/games', replace: true })
  }, [navigate, room.error])

  if (room.isLoading || participants.isLoading)
    return <main className="page-content game-lobby-page"><GeneralLoader label="Loading your game room…" /></main>
  if (!room.data && (room.isError || participants.isError))
    return <main className="page-content game-lobby-page"><GeneralLoader label="Reconnecting to your game room…" onRetry={() => { void room.refetch(); void participants.refetch() }} /></main>
  if (!room.data) return null

  const currentRoom = room.data
  const members = participants.data ?? []
  const error = room.error || participants.error || ready.error || start.error || endRoom.error || saveAbcSettings.error

  return <main className="page-content game-lobby-page">
    <div className="game-lobby-topbar">
      <Link className="text-link" to="/games"><ArrowLeft size={17} /> Back to games</Link>
      {currentRoom.is_host && <button className="button button--small button--danger" type="button" disabled={endRoom.isPending} onClick={() => { if (window.confirm('End this room for everyone?')) endRoom.mutate() }}>{endRoom.isPending ? 'Ending…' : 'End room'}</button>}
    </div>
    <section className="game-lobby-card">
      <div className="game-lobby-heading">
        <span className="game-lobby-icon"><GameController size={28} weight="duotone" /></span>
        <div><span className="eyebrow">Game room lobby</span><h1>{currentRoom.name}</h1><p>{currentRoom.game} · {currentRoom.players} of {currentRoom.max_players} players</p></div>
      </div>
      {currentRoom.invite_token && <button className="game-lobby-share" type="button" onClick={() => {
        const url = `${window.location.origin}/games/rooms/invite/${currentRoom.invite_token}`
        void navigator.clipboard.writeText(url).then(() => { setCopied(true); window.setTimeout(() => setCopied(false), 1800) })
      }}><Copy size={17} /> {copied ? 'Link copied' : 'Copy invite link'}</button>}
      <div className="game-lobby-waiting"><span className="game-lobby-pulse" /> <strong>{currentRoom.is_host ? 'Your room is ready.' : 'Waiting for the host to start…'}</strong><small>Everyone will enter the game automatically when it begins.</small></div>
      {currentRoom.is_host && currentRoom.game === 'CSEC IT Mock Exam' && <div className="exam-invigilator-note"><span className="eyebrow">Invigilator room</span><h2>Invite one candidate</h2><p>Copy the invite link above and send it to the candidate. Their name and email will be collected before they enter the lobby. You can start once they are ready.</p></div>}
      {currentRoom.is_host && currentRoom.game === 'ABC Fast or Slow' && <form className="abc-room-settings" onSubmit={(event) => { event.preventDefault(); saveAbcSettings.mutate() }}>
        <div><span className="eyebrow">ABC host settings</span><h2>Shape this match</h2><p>Choose how many people can join, add categories, and decide whether the majority can reject an answer.</p></div>
        <label>Players who can join<input type="number" min="2" value={abcCapacity} onChange={(event) => setAbcCapacity(Math.max(2, Number(event.target.value) || 2))} /></label>
        <label>Categories <small>Separate with commas</small><input value={abcCategories} onChange={(event) => setAbcCategories(event.target.value)} /></label>
        <label className="abc-room-settings__toggle"><input type="checkbox" checked={abcMajorityInvalid} onChange={(event) => setAbcMajorityInvalid(event.target.checked)} /> Majority-invalid veto: an answer earns no points when most reviewers mark it invalid.</label>
        <button className="button button--secondary" type="submit" disabled={saveAbcSettings.isPending}>{saveAbcSettings.isPending ? 'Saving…' : 'Save ABC settings'}</button>
      </form>}
      <div className="game-lobby-members" aria-label="Room participants">
        {members.map((member) => {
          const isReady = member.is_host || member.ready
          return <article className="game-lobby-member" key={member.user_id}>
            <span className="avatar avatar--sage">{member.avatar_url ? <img src={assetUrl(member.avatar_url)} alt="" /> : member.name.slice(0, 1).toUpperCase()}</span>
            <div><strong>{member.name}</strong><small>{member.is_host ? 'Host · ready to start' : isReady ? 'Ready to play' : 'Getting ready'}</small></div>
            <span className={isReady ? 'lobby-ready lobby-ready--yes' : 'lobby-ready'}><CheckCircle size={18} weight={isReady ? 'fill' : 'regular'} /> {isReady ? 'Ready' : 'Not ready'}</span>
          </article>
        })}
        {Array.from({ length: Math.max(0, currentRoom.max_players - members.length) }, (_, index) => <article className="game-lobby-member game-lobby-member--empty" key={`empty-${index}`}><span className="game-lobby-empty-avatar"><UsersThree size={19} /></span><div><strong>Open seat</strong><small>{currentRoom.fill_with_bots ? 'A friendly bot can fill this seat' : 'Waiting for a player'}</small></div></article>)}
      </div>
      {error && <p className="form-error" role="alert">{error instanceof Error ? error.message : 'The lobby could not update.'}</p>}
      <div className="game-lobby-actions">
        {!currentRoom.is_host && <button className={currentRoom.ready ? 'button button--secondary' : 'button button--primary'} type="button" disabled={ready.isPending} onClick={() => ready.mutate()}>{ready.isPending ? 'Updating…' : currentRoom.ready ? 'Ready ✓' : 'Ready up'}</button>}
        {currentRoom.is_host && <button className="button button--primary" type="button" disabled={start.isPending} onClick={() => {
          if (currentRoom.game.trim().toLowerCase() === 'csec it mock exam') setShowExamStart(true)
          else start.mutate()
        }}>{start.isPending ? 'Starting…' : currentRoom.fill_with_bots ? 'Start game with bots' : 'Start game'}</button>}
      </div>
    </section>
    {showExamStart && currentRoom.game.trim().toLowerCase() === 'csec it mock exam' && <div className="exam-start-modal__backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setShowExamStart(false) }}>
      <section className="exam-start-modal" role="dialog" aria-modal="true" aria-labelledby="exam-start-title">
        <span className="eyebrow">Private mock exam</span>
        <h2 id="exam-start-title">Ready to begin?</h2>
        <p>This is a supervised exam. Paper 1 is auto-marked, and Paper 2 has written answers for you to review and grade from the Invigilator exam desk.</p>
        <div className="exam-start-modal__actions">
          <button className="button button--secondary" type="button" onClick={() => setShowExamStart(false)}>Not yet</button>
          <button className="button button--primary" type="button" disabled={start.isPending} onClick={() => { setShowExamStart(false); start.mutate() }}>{start.isPending ? 'Starting…' : 'Start exam'}</button>
        </div>
      </section>
    </div>}
  </main>
}
