export function playerDisplayName(name: string, seat: number, viewerSeat: number): string {
  return seat === viewerSeat ? `${name} · You` : name
}
