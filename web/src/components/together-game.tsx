import { useEffect, useRef } from 'react'
import Phaser from 'phaser'

type TogetherState = {
  seat_index?: number
  level?: number
  levels_total?: number
  phase?: string
  players?: Array<{ name: string; color: string; x: number; y: number; vx?: number; on_ground?: boolean; connected?: boolean }>
  level_config?: { width: number; checkpoint: number; finish: number; name: string; mechanic: string; theme?: string; cooperation?: string; platforms?: Array<{ x: number; y: number; width: number; height: number }>; hazards?: Array<{ x: number; width: number }>; collectibles?: Array<{ x: number; y: number }>; plates?: Array<{ x: number; label: string }>; moving_platforms?: Array<{ x: number; y: number; width: number; range: number }> }
  finishers?: number[]
  last_event?: string
  levels_completed?: number
  falls?: number
}

type Props = { state: TogetherState; send: (action: Record<string, unknown>) => void; spectator?: boolean }

const ROBOT_VARIANTS = ['purple', 'coral', 'blue', 'green', 'yellow'] as const
const ROBOT_DIRECTIONS = ['south', 'east', 'west', 'north'] as const

class TogetherScene extends Phaser.Scene {
  state: TogetherState = {}
  send: Props['send'] = () => undefined
  spectator = false
  keys!: Record<string, Phaser.Input.Keyboard.Key>
  lastInput = 0
  avatars: Phaser.GameObjects.Container[] = []
  playerSprites: Phaser.GameObjects.Sprite[] = []
  constructor() { super('TogetherScene') }
  create() {
    this.keys = this.input.keyboard!.addKeys('A,D,W,LEFT,RIGHT,UP,SPACE,E') as Record<string, Phaser.Input.Keyboard.Key>
    this.cameras.main.setBackgroundColor('#f8f5f0')
    this.redraw()
  }
  preload() {
    ROBOT_VARIANTS.forEach((variant) => ROBOT_DIRECTIONS.forEach((direction) => {
      this.load.image(`together-robot-${variant}-${direction}`, `/assets/together/pixellab/robot/variants/${variant}/${direction}.png`)
    }))
    this.load.image('together-backdrop', '/assets/together/original/together-beginning-backdrop.webp')
  }
  apply(state: TogetherState) {
    const levelChanged = state.level !== this.state.level || this.avatars.length !== (state.players?.length ?? 0)
    this.state = state
    if (levelChanged) {
      this.redraw()
      return
    }
    state.players?.forEach((player, index) => {
      const avatar = this.avatars[index]
      const sprite = this.playerSprites[index]
      if (!avatar || !sprite) return
      avatar.setPosition(player.x, 480 - (player.y ?? 0))
      const direction = player.vx !== undefined && player.vx < -1 ? 'west' : player.vx !== undefined && player.vx > 1 ? 'east' : 'south'
      sprite.setTexture(`together-robot-${ROBOT_VARIANTS[index] ?? 'purple'}-${direction}`)
    })
  }
  redraw() {
    this.children.removeAll(true)
    const config = this.state.level_config ?? { width: 2200, checkpoint: 700, finish: 1750, name: 'The Beginning', mechanic: 'two-buttons', cooperation: 'Stay together' }
    const viewWidth = this.scale.width
    const scale = Math.min(1, viewWidth / 1100)
    this.cameras.main.setZoom(scale)
    this.cameras.main.setBounds(0, 0, config.width, 620)
    this.add.rectangle(config.width / 2, 310, config.width, 620, 0xf5eee5)
    const themeTint: Record<string, number> = { meadow: 0xffffff, crystal: 0xe7f2ff, sunset: 0xffe5d8, moonlit: 0xdcdcff }
    this.add.image(config.width / 2, 310, 'together-backdrop').setDisplaySize(config.width, 620).setTint(themeTint[config.theme ?? 'meadow'] ?? 0xffffff).setAlpha(0.92).setScrollFactor(0.2)
    for (let index = 0; index < 9; index += 1) {
      const hill = this.add.ellipse(180 + index * 260, 430 - (index % 3) * 22, 420, 190, index % 2 ? 0xded5ed : 0xd8e8df).setAlpha(0.72)
      hill.setScrollFactor(0.28)
    }
    const ground = this.add.rectangle(config.width / 2, 535, config.width, 170, 0xe6ddd1).setStrokeStyle(3, 0xd0c2b1)
    ground.setOrigin(0.5)
    const hud = this.add.container(0, 0).setScrollFactor(0)
    hud.add(this.add.text(36, 28, `WORLD 1  ·  LEVEL ${this.state.level ?? 1}/${this.state.levels_total ?? 20}`, { fontFamily: 'Nunito, sans-serif', fontSize: '20px', color: '#5f5368', fontStyle: 'bold' }))
    hud.add(this.add.text(36, 58, config.name, { fontFamily: 'Nunito, sans-serif', fontSize: '34px', color: '#332d3c', fontStyle: 'bold' }))
    hud.add(this.add.text(36, 100, this.state.last_event ?? 'Stay close. Nobody makes it alone.', { fontFamily: 'Nunito, sans-serif', fontSize: '17px', color: '#6f6574' }))
    hud.add(this.add.text(36, 132, config.cooperation ?? 'Coordinate your timing', { fontFamily: 'Nunito, sans-serif', fontSize: '15px', color: '#8f79d8', fontStyle: 'bold' }))
    for (const platform of config.platforms ?? []) {
      const platformTop = 535 - platform.y
      const graphic = this.add.graphics().fillStyle(0x4f315f).fillRoundedRect(platform.x - platform.width / 2, platformTop, platform.width, platform.height + 20, 10).lineStyle(3, 0x332040).strokeRoundedRect(platform.x - platform.width / 2, platformTop, platform.width, platform.height + 20, 10)
      graphic.fillStyle(0x9bd47d).fillRoundedRect(platform.x - platform.width / 2, platformTop - 5, platform.width, 12, 6)
      graphic.setDepth(2)
    }
    for (const platform of config.moving_platforms ?? []) {
      const platformTop = 535 - platform.y
      const moving = this.add.graphics().fillStyle(0x5d3c70).fillRoundedRect(platform.x - platform.width / 2, platformTop, platform.width, 30, 10).lineStyle(3, 0xffc875).strokeRoundedRect(platform.x - platform.width / 2, platformTop, platform.width, 30, 10)
      moving.fillStyle(0xffd98a).fillRoundedRect(platform.x - platform.width / 2 + 12, platformTop - 4, platform.width - 24, 8, 4)
      moving.setDepth(3)
      this.tweens.add({ targets: moving, x: platform.range, duration: 1700 + platform.range * 2, ease: 'Sine.inOut', yoyo: true, repeat: -1 })
    }
    for (const collectible of config.collectibles ?? []) {
      const crystal = this.add.graphics().fillStyle(0xff80c8, 1).fillTriangle(collectible.x, 420 - collectible.y, collectible.x + 13, 435 - collectible.y, collectible.x, 450 - collectible.y).fillTriangle(collectible.x, 420 - collectible.y, collectible.x - 13, 435 - collectible.y, collectible.x, 450 - collectible.y).lineStyle(2, 0xffe3f4).strokePath()
      crystal.setDepth(4)
      this.tweens.add({ targets: crystal, y: -8, duration: 850 + (collectible.x % 4) * 90, ease: 'Sine.inOut', yoyo: true, repeat: -1 })
    }
    for (const plate of config.plates ?? []) {
      this.add.ellipse(plate.x, 518, 82, 20, 0x8ee6dd, 0.72).setStrokeStyle(3, 0xd7fff7).setDepth(3)
      this.add.text(plate.x - 5, 508, plate.label, { fontFamily: 'Nunito, sans-serif', fontSize: '16px', color: '#3e4768', fontStyle: 'bold' }).setDepth(4)
    }
    for (const hazard of config.hazards ?? []) {
      this.add.rectangle(hazard.x, 495, hazard.width, 18, 0xe895b4).setStrokeStyle(2, 0xc55f86)
      this.add.text(hazard.x + 8, 470, 'oops zone', { fontFamily: 'Nunito, sans-serif', fontSize: '12px', color: '#a64e74' })
    }
    this.add.rectangle(config.checkpoint, 455, 14, 160, 0x8ee6dd).setAlpha(0.7).setDepth(1)
    this.add.text(config.checkpoint - 58, 355, 'CHECKPOINT', { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#d7fff7', fontStyle: 'bold' })
    this.add.rectangle(config.finish, 455, 34, 160, 0xd574ec).setAlpha(0.85).setDepth(1)
    this.add.text(config.finish - 35, 355, 'PORTAL', { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#fff1ff', fontStyle: 'bold' })
    this.add.text(config.width - 460, 75, config.mechanic.replaceAll('-', ' ').toUpperCase(), { fontFamily: 'Nunito, sans-serif', fontSize: '16px', color: '#9a7b9b', fontStyle: 'bold' })
    this.playerSprites = []
    this.avatars = (this.state.players ?? []).map((player, index) => {
      const variant = ROBOT_VARIANTS[index] ?? 'purple'
      const sprite = this.add.sprite(0, 0, `together-robot-${variant}-south`).setOrigin(0.5, 1).setDisplaySize(76, 76)
      const label = this.add.text(-45, 8, player.name, { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#4b4254' })
      this.playerSprites.push(sprite)
      return this.add.container(player.x ?? 150 + index * 52, 480 - (player.y ?? 0), [sprite, label])
    })
  }
  update(time: number) {
    if (this.spectator || !this.keys) return
    const axis = this.keys.LEFT.isDown || this.keys.A.isDown ? -1 : this.keys.RIGHT.isDown || this.keys.D.isDown ? 1 : 0
    const jump = this.keys.SPACE.isDown || this.keys.W.isDown || this.keys.UP.isDown
    const local = this.state.players?.[Number(this.state.seat_index ?? 0)]
    if (axis !== 0 || jump || (local && !local.on_ground)) {
      if (time - this.lastInput > 66) { this.send({ action: 'input', axis, jump, dt: 0.066 }); this.lastInput = time }
    }
    if (local) this.cameras.main.centerOn(local.x, 330)
  }
}

export function TogetherGame({ state, send, spectator = false }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const game = useRef<Phaser.Game | null>(null)
  useEffect(() => {
    if (!host.current) return
    const scene = new TogetherScene()
    scene.state = state
    scene.send = send
    scene.spectator = spectator
    game.current = new Phaser.Game({ type: Phaser.CANVAS, width: 1100, height: 620, parent: host.current, scene, render: { antialias: true, roundPixels: true }, scale: { mode: Phaser.Scale.RESIZE, autoCenter: Phaser.Scale.CENTER_BOTH } })
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
