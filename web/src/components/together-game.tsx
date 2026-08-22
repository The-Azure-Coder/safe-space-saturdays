import { useEffect, useRef } from 'react'
import Phaser from 'phaser'

type TogetherState = {
  seat_index?: number
  level?: number
  levels_total?: number
  phase?: string
  players?: Array<{ name: string; color: string; x: number; y: number; connected?: boolean }>
  level_config?: { width: number; checkpoint: number; finish: number; name: string; mechanic: string }
  finishers?: number[]
  last_event?: string
  levels_completed?: number
  falls?: number
}

type Props = { state: TogetherState; send: (action: Record<string, unknown>) => void; spectator?: boolean }

const palette: Record<string, number> = { purple: 0x8f79d8, pink: 0xe895b4, blue: 0x6fafd7, green: 0x83b99a }

class TogetherScene extends Phaser.Scene {
  state: TogetherState = {}
  send: Props['send'] = () => undefined
  spectator = false
  keys!: Record<string, Phaser.Input.Keyboard.Key>
  lastInput = 0
  avatars: Phaser.GameObjects.Container[] = []
  constructor() { super('TogetherScene') }
  create() {
    this.keys = this.input.keyboard!.addKeys('A,D,W,LEFT,RIGHT,UP,SPACE,E') as Record<string, Phaser.Input.Keyboard.Key>
    this.cameras.main.setBackgroundColor('#f8f5f0')
    this.redraw()
  }
  apply(state: TogetherState) { this.state = state; this.redraw() }
  redraw() {
    this.children.removeAll(true)
    const config = this.state.level_config ?? { width: 2200, checkpoint: 700, finish: 1750, name: 'The Beginning', mechanic: 'two-buttons' }
    const viewWidth = this.scale.width
    const scale = Math.min(1, viewWidth / 1100)
    this.cameras.main.setZoom(scale)
    this.cameras.main.setBounds(0, 0, config.width, 620)
    const ground = this.add.rectangle(config.width / 2, 535, config.width, 170, 0xe6ddd1).setStrokeStyle(3, 0xd0c2b1)
    ground.setOrigin(0.5)
    this.add.text(36, 28, `WORLD 1  ·  LEVEL ${this.state.level ?? 1}/${this.state.levels_total ?? 20}`, { fontFamily: 'Nunito, sans-serif', fontSize: '20px', color: '#5f5368', fontStyle: 'bold' })
    this.add.text(36, 58, config.name, { fontFamily: 'Nunito, sans-serif', fontSize: '34px', color: '#332d3c', fontStyle: 'bold' })
    this.add.text(36, 100, this.state.last_event ?? 'Stay close. Nobody makes it alone.', { fontFamily: 'Nunito, sans-serif', fontSize: '17px', color: '#6f6574' })
    this.add.rectangle(config.checkpoint, 455, 12, 160, 0x9ed2bd).setAlpha(0.75)
    this.add.text(config.checkpoint - 58, 355, 'CHECKPOINT', { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#4f967e' })
    this.add.rectangle(config.finish, 455, 28, 160, 0xf1c476).setAlpha(0.9)
    this.add.text(config.finish - 35, 355, 'FINISH', { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#a26c24' })
    this.add.text(config.width - 460, 75, config.mechanic.replaceAll('-', ' ').toUpperCase(), { fontFamily: 'Nunito, sans-serif', fontSize: '16px', color: '#9a7b9b', fontStyle: 'bold' })
    this.avatars = (this.state.players ?? []).map((player, index) => {
      const body = this.add.circle(0, 0, 22, palette[player.color] ?? 0x8f79d8).setStrokeStyle(4, 0xffffff)
      const face = this.add.circle(-7, -3, 3, 0x332d3c)
      const face2 = this.add.circle(7, -3, 3, 0x332d3c)
      const label = this.add.text(-45, 30, player.name, { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#4b4254' })
      return this.add.container(player.x ?? 150 + index * 52, 480, [body, face, face2, label])
    })
  }
  update(time: number) {
    if (this.spectator || !this.keys) return
    const axis = this.keys.LEFT.isDown || this.keys.A.isDown ? -1 : this.keys.RIGHT.isDown || this.keys.D.isDown ? 1 : 0
    const jump = this.keys.SPACE.isDown || this.keys.W.isDown || this.keys.UP.isDown
    if (axis !== 0 || jump) {
      if (time - this.lastInput > 66) { this.send({ action: 'input', axis, jump, dt: 0.066 }); this.lastInput = time }
    }
    const local = this.state.players?.[Number(this.state.seat_index ?? 0)]
    if (local) this.cameras.main.centerOn(local.x, 330)
  }
}

export function TogetherGame({ state, send, spectator = false }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const game = useRef<Phaser.Game | null>(null)
  const latest = useRef({ state, send, spectator })
  latest.current = { state, send, spectator }
  useEffect(() => {
    if (!host.current) return
    const scene = new TogetherScene()
    scene.state = state
    scene.send = send
    scene.spectator = spectator
    game.current = new Phaser.Game({ type: Phaser.AUTO, width: 1100, height: 620, parent: host.current, scene, render: { antialias: true }, scale: { mode: Phaser.Scale.RESIZE, autoCenter: Phaser.Scale.CENTER_BOTH } })
    return () => { game.current?.destroy(true); game.current = null }
  }, [])
  useEffect(() => {
    const scene = game.current?.scene.getScene('TogetherScene') as TogetherScene | undefined
    if (scene) { scene.send = send; scene.spectator = spectator; scene.apply(state) }
  }, [state, send, spectator])
  const finished = state.phase === 'complete'
  return <section className="together-game" aria-label="Together cooperative platform game">
    <div ref={host} className="together-game__canvas" />
    <div className="together-game__hud"><span>Falls: {state.falls ?? 0}</span><span>Levels: {state.levels_completed ?? 0}/20</span><span>Controls: A/D or arrows · Space to jump</span></div>
    <div className="together-game__mobile-controls" aria-label="Touch controls">
      <button type="button" onPointerDown={() => send({ action: 'input', axis: -1, dt: 0.1 })}>←</button><button type="button" onPointerDown={() => send({ action: 'input', axis: 1, dt: 0.1 })}>→</button><button type="button" onPointerDown={() => send({ action: 'input', axis: 0, jump: true, dt: 0.1 })}>Jump</button>
    </div>
    {finished && <div className="together-game__complete" role="status"><strong>WE MADE IT!</strong><span>20 levels · {state.falls ?? 0} team falls</span><button className="button button--primary" type="button" onClick={() => send({ action: 'play_again' })}>Play again</button></div>}
  </section>
}
