import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocalSearchParams } from 'expo-router'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { mobileApi } from '@/api'
import { ErrorState, Header, Page } from '@/ui'
import { themes } from '@/theme'

type Cell = number | null

export default function MobileGameSession() {
  const { matchId } = useLocalSearchParams<{ matchId: string }>()
  const client = useQueryClient()
  const session = useQuery({
    queryKey: ['mobile-game-session', matchId],
    queryFn: () => mobileApi.gameSession(matchId),
    enabled: Boolean(matchId),
    refetchInterval: 1500,
    refetchOnWindowFocus: true,
  })

  if (session.isPending) return <Page><ActivityIndicator color={themes.sage.primary} size="large" /></Page>
  if (session.isError) return <Page><ErrorState message={session.error.message} onRetry={() => void session.refetch()} /></Page>

  const state = session.data.state ?? {}
  const currentPlayer = Number(state.current_player ?? -1)
  const seat = Number(state.seat_index ?? -1)
  const isMyTurn = currentPlayer === seat
  const submit = async (action: Record<string, unknown>) => {
    await mobileApi.gameAction(matchId, action)
    await client.invalidateQueries({ queryKey: ['mobile-game-session', matchId] })
  }
  const game = session.data.game
  const title = game === 'connect-four' ? 'Connect Four' : game[0].toUpperCase() + game.slice(1)

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <Header eyebrow="LIVE GAME" title={title} copy={statusCopy(state, isMyTurn)} />
      <View style={styles.card}>
        {game === 'connect-four' && <ConnectFour state={state} enabled={isMyTurn} onAction={submit} />}
        {game === 'ludo' && <Ludo state={state} enabled={isMyTurn} onAction={submit} />}
        {game !== 'connect-four' && game !== 'ludo' && <GenericGame state={state} enabled={isMyTurn} onAction={submit} />}
      </View>
      {state.last_event ? <Text style={styles.event}>{String(state.last_event)}</Text> : null}
      {state.winner !== undefined && state.winner !== null ? <Text style={styles.result}>Winner: player {String(Number(state.winner) + 1)}</Text> : null}
    </ScrollView>
  )
}

function statusCopy(state: Record<string, any>, isMyTurn: boolean) {
  if (state.winner !== undefined && state.winner !== null) return 'The match is complete.'
  if (state.draw) return 'A thoughtful draw. Play again when you are ready.'
  return isMyTurn ? 'Your turn — make a move.' : 'The other player is thinking…'
}

function ConnectFour({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const board = (state.board ?? []) as Cell[][]
  return <View>
    <View style={styles.connectBoard}>
      {board.map((row, rowIndex) => row.map((cell, columnIndex) => <View key={`${rowIndex}-${columnIndex}`} style={[styles.connectCell, cell === 0 && styles.connectRed, cell === 1 && styles.connectYellow]} />))}
    </View>
    <View style={styles.columnRow}>
      {Array.from({ length: 7 }, (_, column) => <Pressable key={column} disabled={!enabled} onPress={() => void onAction({ action: 'move', column })} style={[styles.columnButton, !enabled && styles.disabled]}><Text style={styles.columnText}>{column + 1}</Text></Pressable>)}
    </View>
  </View>
}

function Ludo({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const tokens = Array.isArray(state.positions?.[state.seat_index]) ? state.positions[state.seat_index] : []
  const legal = Array.isArray(state.legal_tokens) ? state.legal_tokens : []
  return <View>
    <Text style={styles.instruction}>Roll the die, then choose a glowing token.</Text>
    <Text style={styles.die}>{state.roll ?? '·'}</Text>
    {state.phase === 'roll' ? <Pressable disabled={!enabled} onPress={() => void onAction({ action: 'roll' })} style={[styles.action, !enabled && styles.disabled]}><Text style={styles.actionText}>Roll dice</Text></Pressable> : null}
    <View style={styles.tokenRow}>{tokens.map((position: number, index: number) => <Pressable key={index} disabled={!enabled || !legal.includes(index)} onPress={() => void onAction({ action: 'move', token: index })} style={[styles.token, legal.includes(index) && styles.glow]}><Text style={styles.tokenText}>{position < 0 ? 'HOME' : position}</Text></Pressable>)}</View>
  </View>
}

function GenericGame({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const action = state.phase === 'roll' ? 'roll' : state.phase === 'choosing' ? 'choose_word' : null
  return <View><Text style={styles.instruction}>Your game is connected and updating live.</Text>{action ? <Pressable disabled={!enabled} onPress={() => void onAction({ action })} style={[styles.action, !enabled && styles.disabled]}><Text style={styles.actionText}>{action === 'roll' ? 'Roll dice' : 'Choose a word'}</Text></Pressable> : null}</View>
}

const styles = StyleSheet.create({
  page: { backgroundColor: themes.sage.background, flexGrow: 1, padding: 24, paddingTop: 62 },
  card: { backgroundColor: themes.sage.surface, borderColor: themes.sage.border, borderRadius: 22, borderWidth: 1, marginTop: 24, padding: 18 },
  event: { color: themes.sage.muted, fontSize: 14, marginTop: 16, textAlign: 'center' },
  result: { color: themes.sage.primary, fontSize: 18, fontWeight: '800', marginTop: 18, textAlign: 'center' },
  connectBoard: { backgroundColor: '#426b57', borderRadius: 18, flexDirection: 'row', flexWrap: 'wrap', gap: 7, padding: 12 },
  connectCell: { backgroundColor: '#f8f3eb', borderRadius: 99, height: 35, width: 35 },
  connectRed: { backgroundColor: '#df8170' },
  connectYellow: { backgroundColor: '#f2c665' },
  columnRow: { flexDirection: 'row', gap: 5, justifyContent: 'center', marginTop: 14 },
  columnButton: { alignItems: 'center', backgroundColor: themes.sage.accent, borderRadius: 9, justifyContent: 'center', minHeight: 36, width: 35 },
  columnText: { color: '#fffdf8', fontWeight: '800' },
  instruction: { color: themes.sage.text, fontSize: 16, fontWeight: '700', lineHeight: 23 },
  die: { alignSelf: 'center', color: themes.sage.primary, fontSize: 52, fontWeight: '900', marginVertical: 20 },
  action: { alignItems: 'center', backgroundColor: themes.sage.primary, borderRadius: 12, justifyContent: 'center', minHeight: 48 },
  actionText: { color: '#fffdf8', fontWeight: '800' },
  disabled: { opacity: 0.45 },
  tokenRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 20 },
  token: { alignItems: 'center', backgroundColor: '#e5efe0', borderRadius: 14, justifyContent: 'center', minHeight: 60, minWidth: 60, padding: 8 },
  glow: { borderColor: themes.sage.accent, borderWidth: 3 },
  tokenText: { color: themes.sage.text, fontSize: 11, fontWeight: '800' },
})
