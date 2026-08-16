import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useLocalSearchParams } from 'expo-router'
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import { useRef, useState } from 'react'
import { PanResponder } from 'react-native'
import Svg, { Polyline } from 'react-native-svg'
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
        {game === 'dominoes' && <Dominoes state={state} enabled={isMyTurn} onAction={submit} />}
        {game === 'bingo' && <Bingo state={state} enabled={isMyTurn} onAction={submit} />}
        {game === 'trivia' && <Trivia state={state} enabled={isMyTurn} onAction={submit} />}
        {game === 'scribble' && <Scribble state={state} enabled={isMyTurn} onAction={submit} />}
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

function Dominoes({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const hand = Array.isArray(state.hands?.[state.seat_index]) ? state.hands[state.seat_index] : []
  const moves = Array.isArray(state.legal_moves) ? state.legal_moves : []
  return <View><Text style={styles.instruction}>Board: {(state.board ?? []).map((tile: number[]) => `${tile[0]}|${tile[1]}`).join('  ') || 'Double six opens the round.'}</Text><View style={styles.tileRow}>{hand.map((tile: number[], index: number) => { const move = moves.find((candidate: any) => candidate.tile_index === index); return <Pressable key={`${tile.join('-')}-${index}`} disabled={!enabled || !move} onPress={() => void onAction({ tile_index: index, side: move?.sides?.[0] ?? 'right' })} style={[styles.tile, move && styles.glow]}><Text style={styles.tileText}>{tile[0]} | {tile[1]}</Text></Pressable> })}</View>{enabled && moves.length === 0 ? <Pressable onPress={() => void onAction({ pass: true })} style={styles.action}><Text style={styles.actionText}>Pass turn</Text></Pressable> : null}</View>
}

function Bingo({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const card = (state.card ?? []) as number[][]; const marked = (state.marked ?? []) as boolean[][]
  return <View><Text style={styles.instruction}>Mark the called numbers, then claim a line.</Text><View style={styles.bingo}>{card.map((row, r) => row.map((number, c) => <View key={`${r}-${c}`} style={[styles.bingoCell, marked[r]?.[c] && styles.bingoMarked]}><Text style={styles.bingoText}>{number || '★'}</Text></View>))}</View><Pressable disabled={!enabled} onPress={() => void onAction({ action: 'draw' })} style={[styles.action, !enabled && styles.disabled]}><Text style={styles.actionText}>Draw next number</Text></Pressable><Pressable disabled={!enabled} onPress={() => void onAction({ action: 'claim' })} style={[styles.secondaryAction, !enabled && styles.disabled]}><Text style={styles.secondaryText}>Claim bingo</Text></Pressable></View>
}

function Trivia({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  if (state.phase === 'board') return <View><Text style={styles.instruction}>Choose a category and point value.</Text><View style={styles.clueGrid}>{(state.board ?? []).flatMap((row: any) => row.values.map((value: number) => <Pressable key={`${row.category}-${value}`} disabled={!enabled || (state.used_clues ?? []).includes(`${row.category}:${value}`)} onPress={() => void onAction({ action: 'select_clue', category: row.category, value })} style={styles.clue}><Text style={styles.clueText}>{row.category} · {value}</Text></Pressable>))}</View></View>
  if (state.phase === 'reveal') return <View><Text style={styles.instruction}>Answer revealed. Continue to the next clue.</Text><Pressable onPress={() => void onAction({ action: 'next' })} style={styles.action}><Text style={styles.actionText}>Next clue</Text></Pressable></View>
  return <View><Text style={styles.instruction}>{state.question}</Text>{(state.options ?? []).map((option: string, index: number) => <Pressable key={option} disabled={!enabled} onPress={() => void onAction({ answer: index })} style={[styles.option, !enabled && styles.disabled]}><Text style={styles.optionText}>{String.fromCharCode(65 + index)}. {option}</Text></Pressable>)}</View>
}

function Scribble({ state, enabled, onAction }: { state: Record<string, any>; enabled: boolean; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const [guess, setGuess] = useState('')
  if (state.phase === 'choosing' && state.is_drawer) return <View><Text style={styles.instruction}>Choose the word you can draw best.</Text>{(state.word_choices ?? []).map((word: string) => <Pressable key={word} onPress={() => void onAction({ action: 'choose_word', word })} style={styles.option}><Text style={styles.optionText}>{word}</Text></Pressable>)}</View>
  return <View><Text style={styles.instruction}>{state.is_drawer ? `Draw: ${state.word ?? 'your chosen word'}` : `Guess: ${state.hint ?? '___'}`}</Text>{state.is_drawer && state.phase === 'drawing' ? <DrawingCanvas state={state} onAction={onAction} /> : null}{!state.is_drawer && ['drawing', 'guessing'].includes(state.phase) ? <><TextInput value={guess} onChangeText={setGuess} placeholder="Your guess" placeholderTextColor={themes.sage.muted} style={styles.input} /><Pressable disabled={!guess.trim()} onPress={() => { void onAction({ action: 'guess', text: guess }); setGuess('') }} style={[styles.action, !guess.trim() && styles.disabled]}><Text style={styles.actionText}>Send guess</Text></Pressable></> : null}</View>
}

function DrawingCanvas({ state, onAction }: { state: Record<string, any>; onAction: (action: Record<string, unknown>) => Promise<void> }) {
  const [color, setColor] = useState('#17231e'); const [draft, setDraft] = useState<{ x: number; y: number }[]>([]); const draftRef = useRef<{ x: number; y: number }[]>([]); const width = 320; const height = 240
  const drawPoints = (points: { x: number; y: number }[]) => points.map((point) => `${point.x * width},${point.y * height}`).join(' ')
  const responder = PanResponder.create({ onStartShouldSetPanResponder: () => true, onPanResponderGrant: (event) => { const point = { x: Math.max(0, Math.min(1, event.nativeEvent.locationX / width)), y: Math.max(0, Math.min(1, event.nativeEvent.locationY / height)) }; draftRef.current = [point]; setDraft([point]) }, onPanResponderMove: (event) => { const point = { x: Math.max(0, Math.min(1, event.nativeEvent.locationX / width)), y: Math.max(0, Math.min(1, event.nativeEvent.locationY / height)) }; draftRef.current = [...draftRef.current, point]; setDraft(draftRef.current) }, onPanResponderRelease: () => { const points = draftRef.current; if (points.length >= 2) void onAction({ action: 'stroke', points, color, size: color === '#fffdf8' ? 18 : 5, erase: color === '#fffdf8' }); draftRef.current = []; setDraft([]) } })
  const strokes = [...(state.strokes ?? []), ...(draft.length > 1 ? [{ points: draft, color, size: 5 }] : [])]
  return <View><View style={styles.canvas} {...responder.panHandlers}><Svg width={width} height={height}>{strokes.map((stroke: any, index: number) => <Polyline key={index} points={drawPoints(stroke.points)} fill="none" stroke={stroke.color} strokeWidth={stroke.size} strokeLinecap="round" strokeLinejoin="round" />)}</Svg></View><View style={styles.palette}>{['#17231e', '#df6f5b', '#4d83c4', '#e4b74c', '#8a5cc7', '#fffdf8'].map((option) => <Pressable key={option} onPress={() => setColor(option)} style={[styles.swatch, { backgroundColor: option }, color === option && styles.selectedSwatch]} />)}<Pressable onPress={() => void onAction({ action: 'clear' })} style={styles.clear}><Text style={styles.clearText}>Clear</Text></Pressable></View><Pressable onPress={() => void onAction({ action: 'end_turn' })} style={styles.action}><Text style={styles.actionText}>Finish drawing</Text></Pressable></View>
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
  tileRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginTop: 20 },
  tile: { backgroundColor: '#f7f0df', borderRadius: 9, padding: 12 },
  tileText: { color: '#243d32', fontWeight: '800' },
  bingo: { flexDirection: 'row', flexWrap: 'wrap', gap: 5, marginVertical: 18 },
  bingoCell: { alignItems: 'center', backgroundColor: '#f7f0df', borderRadius: 7, height: 50, justifyContent: 'center', width: 50 },
  bingoMarked: { backgroundColor: themes.sage.accent },
  bingoText: { color: '#243d32', fontWeight: '800' },
  secondaryAction: { alignItems: 'center', borderColor: themes.sage.border, borderRadius: 12, borderWidth: 1, justifyContent: 'center', marginTop: 12, minHeight: 48 },
  secondaryText: { color: themes.sage.text, fontWeight: '800' },
  clueGrid: { gap: 8, marginTop: 18 },
  clue: { backgroundColor: '#e5efe0', borderRadius: 10, padding: 12 },
  clueText: { color: themes.sage.primary, fontWeight: '800' },
  option: { backgroundColor: '#e5efe0', borderRadius: 12, marginTop: 10, padding: 14 },
  optionText: { color: themes.sage.text, fontSize: 15, fontWeight: '700' },
  input: { backgroundColor: themes.sage.background, borderColor: themes.sage.border, borderRadius: 12, borderWidth: 1, color: themes.sage.text, fontSize: 16, marginTop: 14, padding: 13 },
  canvas: { backgroundColor: '#fffdf8', borderColor: themes.sage.border, borderRadius: 14, borderWidth: 1, height: 240, marginTop: 16, overflow: 'hidden', width: '100%' },
  palette: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginVertical: 12 },
  swatch: { borderColor: '#ffffff', borderRadius: 99, borderWidth: 1, height: 28, width: 28 },
  selectedSwatch: { borderColor: themes.sage.primary, borderWidth: 3 },
  clear: { borderColor: themes.sage.border, borderRadius: 9, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 7 },
  clearText: { color: themes.sage.primary, fontWeight: '800' },
})
