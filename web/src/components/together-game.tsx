import { useEffect, useRef } from 'react'
import Phaser from 'phaser'

type TogetherState = {
  seat_index?: number
  level?: number
  levels_total?: number
  phase?: string
  players?: Array<{ name: string; color: string; x: number; y: number; vx?: number; on_ground?: boolean; connected?: boolean }>
  level_config?: { width: number; checkpoint: number; finish: number; name: string; mechanic: string; cooperation?: string; platforms?: Array<{ x: number; y: number; width: number; height: number }>; hazards?: Array<{ x: number; width: number }> }
  finishers?: number[]
  last_event?: string
  levels_completed?: number
  falls?: number
}

type Props = { state: TogetherState; send: (action: Record<string, unknown>) => void; spectator?: boolean }

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
    this.anims.create({ key: 'together-ninja-run', frames: this.anims.generateFrameNumbers('ninja-hero', { start: 1, end: 6 }), frameRate: 10, repeat: -1 })
    this.anims.create({ key: 'together-ninja-idle', frames: [{ key: 'ninja-hero', frame: 0 }, { key: 'ninja-hero', frame: 1 }], frameRate: 3, repeat: -1 })
    this.redraw()
  }
  preload() {
    this.load.spritesheet('ninja-hero', '/assets/together/reference/images/ninja-hero.png', { frameWidth: 36, frameHeight: 42 })
    this.load.image('ninja-background', '/assets/together/reference/images/ninja-background.png')
    this.load.image('ninja-ground', '/assets/together/reference/images/ninja-ground.png')
    this.load.spritesheet('ninja-decor', '/assets/together/reference/images/ninja-decor.png', { frameWidth: 42, frameHeight: 42 })
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
      sprite.play(Math.abs(player.vx ?? 0) > 1 ? 'together-ninja-run' : 'together-ninja-idle', true)
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
    this.add.image(config.width / 2, 238, 'ninja-background').setDisplaySize(config.width, 500).setAlpha(0.28).setScrollFactor(0.2)
    for (let index = 0; index < 9; index += 1) {
      const hill = this.add.ellipse(180 + index * 260, 430 - (index % 3) * 22, 420, 190, index % 2 ? 0xded5ed : 0xd8e8df).setAlpha(0.72)
      hill.setScrollFactor(0.28)
    }
    const ground = this.add.rectangle(config.width / 2, 535, config.width, 170, 0xe6ddd1).setStrokeStyle(3, 0xd0c2b1)
    ground.setOrigin(0.5)
    this.add.tileSprite(config.width / 2, 535, config.width, 84, 'ninja-ground').setAlpha(0.82).setDepth(1)
    for (let index = 0; index < Math.ceil(config.width / 180); index += 1) {
      this.add.sprite(90 + index * 180, 480, 'ninja-decor', index % 5).setAlpha(0.72).setDepth(1)
    }
    const hud = this.add.container(0, 0).setScrollFactor(0)
    hud.add(this.add.text(36, 28, `WORLD 1  ·  LEVEL ${this.state.level ?? 1}/${this.state.levels_total ?? 20}`, { fontFamily: 'Nunito, sans-serif', fontSize: '20px', color: '#5f5368', fontStyle: 'bold' }))
    hud.add(this.add.text(36, 58, config.name, { fontFamily: 'Nunito, sans-serif', fontSize: '34px', color: '#332d3c', fontStyle: 'bold' }))
    hud.add(this.add.text(36, 100, this.state.last_event ?? 'Stay close. Nobody makes it alone.', { fontFamily: 'Nunito, sans-serif', fontSize: '17px', color: '#6f6574' }))
    hud.add(this.add.text(36, 132, config.cooperation ?? 'Coordinate your timing', { fontFamily: 'Nunito, sans-serif', fontSize: '15px', color: '#8f79d8', fontStyle: 'bold' }))
    for (const platform of config.platforms ?? []) {
      const graphic = this.add.graphics().fillStyle(0xb59bd9).fillRoundedRect(platform.x - platform.width / 2, 535 - platform.y, platform.width, platform.height, 10).lineStyle(3, 0x8f79d8).strokeRoundedRect(platform.x - platform.width / 2, 535 - platform.y, platform.width, platform.height, 10)
      graphic.setDepth(2)
    }
    for (const hazard of config.hazards ?? []) {
      this.add.rectangle(hazard.x, 495, hazard.width, 18, 0xe895b4).setStrokeStyle(2, 0xc55f86)
      this.add.text(hazard.x + 8, 470, 'oops zone', { fontFamily: 'Nunito, sans-serif', fontSize: '12px', color: '#a64e74' })
    }
    this.add.rectangle(config.checkpoint, 455, 12, 160, 0x9ed2bd).setAlpha(0.75).setDepth(1)
    this.add.text(config.checkpoint - 58, 355, 'CHECKPOINT', { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#4f967e' })
    this.add.rectangle(config.finish, 455, 28, 160, 0xf1c476).setAlpha(0.9).setDepth(1)
    this.add.text(config.finish - 35, 355, 'FINISH', { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#a26c24' })
    this.add.text(config.width - 460, 75, config.mechanic.replaceAll('-', ' ').toUpperCase(), { fontFamily: 'Nunito, sans-serif', fontSize: '16px', color: '#9a7b9b', fontStyle: 'bold' })
    this.playerSprites = []
    this.avatars = (this.state.players ?? []).map((player, index) => {
      const sprite = this.add.sprite(0, -42, 'ninja-hero', 0).setScale(1.75).setTint(Phaser.Display.Color.HexStringToColor(player.color ?? '#8f79d8').color)
      sprite.play('together-ninja-idle')
      const label = this.add.text(-45, 30, player.name, { fontFamily: 'Nunito, sans-serif', fontSize: '14px', color: '#4b4254' })
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
